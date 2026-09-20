"""Fetch deep XAU_USD M1 history from OANDA and splice it onto the existing 3y file.

Why this exists
---------------
`m3_scalper/xau_m1_3y.parquet` covers 2023-07-02 -> 2026-07-23 (3.06 years). The
conjunction test's power analysis showed that span yields only ~454 tradeable
events on the method's own preferred timeframe stack, giving a ~7.2pp minimum
detectable effect against a plausible 3-5pp true effect -- the test cannot
settle the question. OANDA's practice API serves XAU_USD M1 back to
2010-01-03, ~16.5 years, which both lifts the event count and spans genuinely
different regimes (2011 peak, the 2013-2015 bear market) rather than the single
bull run the 3y file contains.

What it does
------------
1. Pages the OANDA candles endpoint (5000-candle cap) from 2010-01-01 up to the
   start of the existing 3y file, plus a deliberate overlap window so the seam
   can be checked rather than assumed.
2. Checkpoints every N pages into `m3_scalper/_xau_hist_cache/` so a killed run
   resumes where it stopped instead of re-fetching hours of history.
3. Splices history + existing 3y into `m3_scalper/xau_m1_full.parquet` with the
   exact schema of the 3y file, so `bars.load_m1(path)` reads it unchanged.

Nothing is repaired silently. Overlap disagreement at the seam is reported, not
smoothed; audit-worthy statistics are left for `meta/xau_history_audit.md`.

Usage (from research/):
    python python/fetch_xau_history.py fetch     # resume-safe, long-running
    python python/fetch_xau_history.py splice    # build the combined parquet
    python python/fetch_xau_history.py status    # how far the cache got
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

RD_ROOT = Path(__file__).resolve().parents[2]        # ...\ClaudeTradingRD
M3 = RD_ROOT / "m3_scalper"
CACHE = M3 / "_xau_hist_cache"                       # own namespace, no collisions
PROGRESS = CACHE / "xau_hist_progress.json"
EXISTING = M3 / "xau_m1_3y.parquet"
OUT = M3 / "xau_m1_full.parquet"

HOST = "https://api-fxpractice.oanda.com"
INSTRUMENT = "XAU_USD"
PAGE = 5000                                          # OANDA hard cap
START = pd.Timestamp("2010-01-01T00:00:00Z")
OVERLAP_DAYS = 5                                     # fetch past the 3y start
FLUSH_PAGES = 20                                     # checkpoint cadence
PACE_S = 0.12                                        # polite gap between requests
MAX_RETRIES = 6


def api_key() -> str:
    """Practice key: env override, else the default already in fetch_oanda_m1.py.

    Loaded by import rather than copied so the credential exists in exactly one
    place in the repo. Never printed, never written to disk.
    """
    if os.environ.get("OANDA_API_KEY"):
        return os.environ["OANDA_API_KEY"]
    src = RD_ROOT / "fetch_oanda_m1.py"
    spec = importlib.util.spec_from_file_location("_fetch_oanda_m1", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.API_KEY


# ---------------------------------------------------------------- fetching


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {api_key()}"
    s.headers["Accept-Datetime-Format"] = "RFC3339"
    return s


def _get_page(sess: requests.Session, frm: pd.Timestamp) -> list[dict]:
    """One page of candles from `frm`, with backoff on 429/5xx/transport errors."""
    params = {
        "granularity": "M1",
        "count": PAGE,
        "price": "M",
        "from": frm.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    delay = 2.0
    for attempt in range(MAX_RETRIES):
        try:
            r = sess.get(
                f"{HOST}/v3/instruments/{INSTRUMENT}/candles",
                params=params, timeout=60,
            )
            if r.status_code == 200:
                return r.json()["candles"]
            if r.status_code in (429, 500, 502, 503, 504):
                # Transient: rate limit or OANDA-side wobble. Back off and retry.
                wait = float(r.headers.get("Retry-After", delay))
                print(f"  [{r.status_code}] retry in {wait:.0f}s "
                      f"({attempt + 1}/{MAX_RETRIES})", flush=True)
                time.sleep(wait)
                delay = min(delay * 2, 120)
                continue
            # 4xx other than 429 is a request-shape problem; retrying won't help.
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        except (requests.Timeout, requests.ConnectionError) as exc:
            print(f"  [net] {type(exc).__name__} retry in {delay:.0f}s "
                  f"({attempt + 1}/{MAX_RETRIES})", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 120)
    raise RuntimeError(f"page from {frm} failed after {MAX_RETRIES} attempts")


def _load_progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {"cursor": START.isoformat(), "chunks": [], "bars": 0, "pages": 0}


def _save_progress(state: dict) -> None:
    PROGRESS.write_text(json.dumps(state, indent=2))


def _flush(rows: list[tuple], state: dict) -> None:
    """Write buffered rows to a numbered chunk parquet and record it."""
    if not rows:
        return
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close",
                                     "volume"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    name = f"chunk_{len(state['chunks']):04d}.parquet"
    df.to_parquet(CACHE / name, index=False)
    state["chunks"].append(name)
    state["bars"] += len(df)
    _save_progress(state)


def fetch(end: pd.Timestamp | None = None) -> None:
    """Page 2010-01-01 -> `end`, checkpointing so a kill is recoverable."""
    CACHE.mkdir(parents=True, exist_ok=True)
    if end is None:
        end = existing_start() + pd.Timedelta(days=OVERLAP_DAYS)

    state = _load_progress()
    cursor = pd.Timestamp(state["cursor"])
    if cursor >= end:
        print(f"already complete: cursor {cursor} >= end {end}")
        return
    print(f"fetching {cursor} -> {end}  (resuming at page {state['pages']}, "
          f"{state['bars']:,} bars cached)", flush=True)

    sess = _session()
    rows: list[tuple] = []
    since_flush = 0
    t0 = time.time()

    while cursor < end:
        candles = _get_page(sess, cursor)
        state["pages"] += 1
        since_flush += 1

        if not candles:
            # No candles in this window at all. Gold has multi-day holiday and
            # weekend closures; jump a week rather than spinning on the cursor.
            cursor = cursor + pd.Timedelta(days=7)
            state["cursor"] = cursor.isoformat()
            if since_flush >= FLUSH_PAGES:
                _flush(rows, state); rows = []; since_flush = 0
            continue

        for cd in candles:
            if not cd["complete"]:
                continue
            t = pd.Timestamp(cd["time"])
            if t >= end:
                continue
            m = cd["mid"]
            rows.append((cd["time"], float(m["o"]), float(m["h"]),
                         float(m["l"]), float(m["c"]), int(cd["volume"])))

        last = pd.Timestamp(candles[-1]["time"])
        nxt = last + pd.Timedelta(minutes=1)
        if nxt <= cursor:                        # no forward progress -> bail
            print(f"\ncursor stalled at {cursor}; stopping")
            break
        cursor = nxt
        state["cursor"] = cursor.isoformat()

        if since_flush >= FLUSH_PAGES:
            _flush(rows, state); rows = []; since_flush = 0
            el = time.time() - t0
            print(f"\r{cursor.date()}  {state['bars']:,} bars  "
                  f"{state['pages']} pages  {el / 60:.1f}m", end="", flush=True)

        time.sleep(PACE_S)

    _flush(rows, state)
    state["cursor"] = min(cursor, end).isoformat()
    _save_progress(state)
    print(f"\ndone: {state['bars']:,} bars in {len(state['chunks'])} chunks, "
          f"cursor {state['cursor']}")


# ---------------------------------------------------------------- splicing


def existing_start() -> pd.Timestamp:
    df = pd.read_parquet(EXISTING, columns=["time"])
    return pd.Timestamp(df["time"].min())


def load_cache() -> pd.DataFrame:
    """All checkpoint chunks concatenated, deduplicated, sorted."""
    state = _load_progress()
    frames = [pd.read_parquet(CACHE / c) for c in state["chunks"]]
    if not frames:
        raise RuntimeError("no cached chunks; run `fetch` first")
    df = pd.concat(frames, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return (df.drop_duplicates("time").sort_values("time")
              .reset_index(drop=True))


def splice(verbose: bool = True) -> pd.DataFrame:
    """Combine fetched history with the existing 3y file, reporting the seam."""
    hist = load_cache()
    old = pd.read_parquet(EXISTING)
    old["time"] = pd.to_datetime(old["time"], utc=True)

    seam = old["time"].min()
    overlap = hist[hist["time"] >= seam]
    report: dict = {
        "seam": str(seam),
        "hist_bars": int(len(hist)),
        "hist_span": [str(hist["time"].min()), str(hist["time"].max())],
        "old_bars": int(len(old)),
        "overlap_bars": int(len(overlap)),
    }

    if len(overlap):
        # Same timestamps fetched twice, months apart, from the same broker.
        # If they disagree the two halves are not the same series and the
        # splice would be quietly fictional -- so measure before joining.
        j = overlap.merge(old, on="time", suffixes=("_new", "_old"))
        report["overlap_matched"] = int(len(j))
        for c in ("open", "high", "low", "close"):
            d = (j[f"{c}_new"] - j[f"{c}_old"]).abs()
            report[f"maxdiff_{c}"] = float(d.max()) if len(d) else None
            report[f"ndiff_{c}"] = int((d > 1e-9).sum()) if len(d) else 0

    # The existing file is authoritative where the two overlap: it is what
    # every prior result in this project was computed on.
    hist_only = hist[hist["time"] < seam][["time", "open", "high", "low", "close"]]
    combined = pd.concat([hist_only, old], ignore_index=True)
    combined["time"] = pd.to_datetime(combined["time"], utc=True)
    combined = (combined.drop_duplicates("time").sort_values("time")
                        .reset_index(drop=True))
    for c in ("open", "high", "low", "close"):
        combined[c] = combined[c].astype("float64")

    # Price continuity across the join: a broker/feed change would show up as a
    # step that no 1-minute gold bar could produce.
    i = int(combined["time"].searchsorted(seam))
    if 0 < i < len(combined):
        prev, first = combined.iloc[i - 1], combined.iloc[i]
        report["seam_prev_bar"] = str(prev["time"])
        report["seam_prev_close"] = float(prev["close"])
        report["seam_first_open"] = float(first["open"])
        report["seam_jump"] = float(first["open"] - prev["close"])
        report["seam_gap_minutes"] = float(
            (first["time"] - prev["time"]).total_seconds() / 60)

    report["combined_bars"] = int(len(combined))
    report["combined_span"] = [str(combined["time"].min()),
                               str(combined["time"].max())]
    if verbose:
        print(json.dumps(report, indent=2))
    return combined


def write_out() -> None:
    combined = splice()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(OUT, index=False)
    print(f"wrote {OUT}: {len(combined):,} bars")


def status() -> None:
    state = _load_progress()
    print(json.dumps({k: v for k, v in state.items() if k != "chunks"}, indent=2))
    print(f"chunks: {len(state['chunks'])}")


# ---------------------------------------------------------------- hole patch

# Two full trading days are absent from the *existing* 3y file, and therefore
# from the splice. Both were re-probed against OANDA and are served in full
# (1376 M1 bars each), so they are a defect of xau_m1_3y.parquet rather than a
# market closure. They are deliberately NOT repaired in xau_m1_full.parquet:
# leaving the splice byte-faithful to the 3y file is what keeps every result
# already computed on the 3y file reproducible on the full file. Patching is
# opt-in and writes a separate file so the choice stays with the caller.
KNOWN_HOLES = [
    ("2025-12-09T00:00:00Z", "2025-12-10T00:00:00Z"),
    ("2026-01-21T00:00:00Z", "2026-01-22T00:00:00Z"),
]
PATCHED = M3 / "xau_m1_full_patched.parquet"


def patch_holes() -> None:
    """Write xau_m1_full_patched.parquet = full series + the two missing days."""
    base = pd.read_parquet(OUT)
    base["time"] = pd.to_datetime(base["time"], utc=True)
    sess = _session()
    add = []
    for lo, hi in KNOWN_HOLES:
        lo_t, hi_t = pd.Timestamp(lo), pd.Timestamp(hi)
        got = 0
        cur = lo_t
        while cur < hi_t:
            candles = _get_page(sess, cur)
            if not candles:
                break
            for cd in candles:
                t = pd.Timestamp(cd["time"])
                if cd["complete"] and lo_t <= t < hi_t:
                    m = cd["mid"]
                    add.append((cd["time"], float(m["o"]), float(m["h"]),
                                float(m["l"]), float(m["c"])))
                    got += 1
            nxt = pd.Timestamp(candles[-1]["time"]) + pd.Timedelta(minutes=1)
            if nxt <= cur:
                break
            cur = nxt
        print(f"{lo[:10]}: +{got} bars")
    new = pd.DataFrame(add, columns=["time", "open", "high", "low", "close"])
    new["time"] = pd.to_datetime(new["time"], utc=True)
    out = pd.concat([base, new], ignore_index=True)
    out = (out.drop_duplicates("time").sort_values("time").reset_index(drop=True))
    for c in ("open", "high", "low", "close"):
        out[c] = out[c].astype("float64")
    out.to_parquet(PATCHED, index=False)
    print(f"wrote {PATCHED}: {len(out):,} bars (+{len(out) - len(base):,})")


# ---------------------------------------------------------------- auditing


TRADING_CAL = (
    "Gold trades ~23h/day: Sunday 18:00 -> Friday 17:00 New York, with a daily "
    "break 17:00-18:04 NY, hence zero bars in NY hour 17 and none on Saturday."
)


def audit(path: Path = OUT) -> dict:
    """Per-year coverage, gap profile, quality checks and regime stats.

    Nothing here repairs the data. Every defect is counted and left in place so
    the decision about which span can carry a backtest is made on the numbers
    rather than on a cleaned series that hides them.
    """
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)
    ny = df["time"].dt.tz_convert("America/New_York")
    df["year"] = ny.dt.year
    df["ny_hour"] = ny.dt.hour
    df["ny_dow"] = ny.dt.dayofweek

    # Volume lives only in the fetched chunks (the 3y file has no volume
    # column), so thin-bar counts are reported for the historical span only.
    try:
        vol = load_cache()[["time", "volume"]]
        vol["time"] = pd.to_datetime(vol["time"], utc=True)
    except Exception:
        vol = None

    out: dict = {"calendar_convention": TRADING_CAL, "years": {}}
    gap = df["time"].diff().dt.total_seconds().div(60)

    for y, g in df.groupby("year"):
        idx = g.index
        gy = gap.loc[idx].iloc[1:]
        c = g["close"].to_numpy()
        o, h, l = (g[k].to_numpy() for k in ("open", "high", "low"))
        # Bar-to-bar return, restricted to consecutive minutes so weekend and
        # holiday reopenings are not counted as intraminute jumps.
        consec = gy.to_numpy() == 1.0
        r = pd.Series(c).pct_change().to_numpy()[1:]
        r_intra = r[consec]
        rec = {
            "bars": int(len(g)),
            "first": str(g["time"].iloc[0]),
            "last": str(g["time"].iloc[-1]),
            "days_with_bars": int(ny.loc[idx].dt.date.nunique()),
            # gap profile
            "hour17_bars": int((g["ny_hour"] == 17).sum()),
            "saturday_bars": int((g["ny_dow"] == 5).sum()),
            "sunday_bars": int((g["ny_dow"] == 6).sum()),
            "hours_present": int(g["ny_hour"].nunique()),
            "gaps_gt_5min": int((gy > 5).sum()),
            "gaps_gt_60min": int((gy > 60).sum()),
            "gaps_gt_1day_not_weekend": int(
                ((gy > 1500) & (~g["ny_dow"].iloc[1:].isin([6, 0]).to_numpy())).sum()),
            "max_gap_hours": float(gy.max() / 60) if len(gy) else 0.0,
            "pct_minutes_filled": None,
            # quality
            "dupe_times": int(g["time"].duplicated().sum()),
            "high_lt_low": int((h < l).sum()),
            "zero_range": int((h == l).sum()),
            "open_outside": int(((o > h) | (o < l)).sum()),
            "close_outside": int(((c > h) | (c < l)).sum()),
            "nonpositive_price": int((l <= 0).sum()),
            "jump_gt_1pct_1min": int((abs(r_intra) > 0.01).sum()),
            "jump_gt_2pct_1min": int((abs(r_intra) > 0.02).sum()),
            # regime
            "low": float(l.min()),
            "high": float(h.max()),
            "first_close": float(c[0]),
            "last_close": float(c[-1]),
            "ret_pct": float((c[-1] / c[0] - 1) * 100),
        }
        # Realised vol from NY-day closes rather than 1-minute returns: at M1
        # the statistic is dominated by microstructure noise, and the noise
        # level itself changes across the span (see zero_range), so a minute
        # based number would confound volatility with data granularity.
        day = g.set_index(ny.loc[idx])
        dclose = day["close"].resample("1D").last().dropna()
        dhigh = day["high"].resample("1D").max().dropna()
        dlow = day["low"].resample("1D").min().dropna()
        dret = pd.Series(dclose.to_numpy()).pct_change().dropna()
        rec["trading_days"] = int(len(dclose))
        rec["ann_vol_pct"] = (float(dret.std(ddof=1) * (252 ** 0.5) * 100)
                              if len(dret) > 2 else None)
        rng = ((dhigh - dlow) / dclose * 100).dropna()
        rec["median_daily_range_pct"] = float(rng.median()) if len(rng) else None
        rec["median_daily_range_usd"] = float((dhigh - dlow).median()) if len(dhigh) else None
        # Expected minutes if the stated calendar held perfectly.
        span_days = (g["time"].iloc[-1] - g["time"].iloc[0]).total_seconds() / 86400
        expected = span_days * (5 / 7) * 23 * 60
        rec["pct_minutes_filled"] = float(100 * len(g) / expected) if expected else None
        if vol is not None:
            vy = vol[(vol["time"] >= g["time"].iloc[0]) & (vol["time"] <= g["time"].iloc[-1])]
            rec["volume_bars"] = int(len(vy))
            rec["vol_eq_1"] = int((vy["volume"] == 1).sum()) if len(vy) else None
            rec["vol_median"] = float(vy["volume"].median()) if len(vy) else None
        out["years"][int(y)] = rec

    out["total_bars"] = int(len(df))
    out["span"] = [str(df["time"].iloc[0]), str(df["time"].iloc[-1])]
    out["dupe_times_total"] = int(df["time"].duplicated().sum())
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    if cmd == "fetch":
        fetch()
    elif cmd == "splice":
        write_out()
    elif cmd == "status":
        status()
    elif cmd == "audit":
        print(json.dumps(audit(), indent=2, default=str))
    elif cmd == "patch-holes":
        patch_holes()
    else:
        raise SystemExit(
            f"unknown command {cmd!r} (fetch|splice|status|audit|patch-holes)")
