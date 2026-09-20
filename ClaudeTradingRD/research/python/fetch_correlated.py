"""Fetch correlated-asset OHLC from OANDA (practice) for the SMT layer.

The TTrades bias layer (`meta/ttrades_method_spec.md` §2.6) needs a *correlated
asset* to test SMT / divergence against. Only XAUUSD exists locally, so this
module pulls the standard gold correlate — **XAG_USD (silver)** — plus a
documented **proxy** for the dollar index.

Scope decisions, deliberately narrow:

* **H1 and D only.** SMT is used at the *bias* layer (daily / 4H / hourly), so
  M1 silver would be ~215 paginated requests for data no rule reads.
* **UTC-aligned daily candles.** OANDA's default daily alignment is 17:00
  New York; that would not line up with the gold series, whose daily candles come
  from `bars.resample(load_m1(), "1D")` on a UTC index. We therefore request
  `alignmentTimezone=UTC, dailyAlignment=0` so the two series share bar edges.
  If you want the 18:00-NY daily candle of §1.4, resample the H1 frame instead —
  do not mix the two.
* **DXY is NOT available on OANDA.** There is no dollar-index instrument on the
  practice feed. `USB10Y_USD` is a bond yield, not the dollar, and is not a
  substitute. What we fetch instead is **EUR_USD, to be used INVERTED as a
  dollar proxy** (EURUSD is ~57% of the DXY basket by weight). This is a proxy,
  not the index: it carries euro-specific risk that DXY averages away, and any
  finding resting on it must say "EURUSD-inverted proxy", never "DXY".

Note the spec's own position (§2.6, `intermarket-correlation-not-used`): TTrades
says he does **not** use cross-asset-class correlation — no DXY-vs-gold — on the
claim that it broke down. Silver is the correlate the method would actually
sanction for gold; the dollar proxy is fetched only so the claim itself can be
checked rather than assumed.

Usage (from research/):
    python python/fetch_correlated.py              # default window + instruments
    python python/fetch_correlated.py --dry-run    # print plan, touch no network

Writes parquet to ClaudeTradingRD/m3_scalper/ (untracked on purpose — large data
must not enter git).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

RD_ROOT = Path(__file__).resolve().parents[2]          # ...\ClaudeTradingRD
OUT_DIR = RD_ROOT / "m3_scalper"

HOST = "https://api-fxpractice.oanda.com"
# Reuse the practice key already carried by the repo's own fetch_oanda_m1.py
# default rather than minting a second secret in a second place.
_REPO_FETCHER = RD_ROOT / "fetch_oanda_m1.py"

# The gold series window: m3_scalper/xau_m1_3y.parquet runs 2023-07-02 -> 2026-07-23.
DEFAULT_START = "2023-07-02T00:00:00Z"
DEFAULT_END = "2026-07-23T23:59:00Z"

# instrument -> (granularity, output filename)
TARGETS: list[tuple[str, str, str]] = [
    ("XAG_USD", "H1", "xag_h1.parquet"),
    ("XAG_USD", "D", "xag_d1.parquet"),
    ("EUR_USD", "H1", "eur_h1.parquet"),
    ("EUR_USD", "D", "eur_d1.parquet"),
]

MAX_COUNT = 5000        # OANDA's hard cap per request


def _api_key() -> str:
    """Practice key: env var first, else the default already in fetch_oanda_m1.py.

    Parsed out of the sibling script rather than copy-pasted so there is exactly
    one literal of it in the repo.
    """
    env = os.environ.get("OANDA_API_KEY")
    if env:
        return env
    if _REPO_FETCHER.exists():
        for line in _REPO_FETCHER.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith('"') and s.endswith('",') and len(s) > 40 and "-" in s:
                return s[1:-2]
    raise RuntimeError(
        "no OANDA key: set OANDA_API_KEY or keep fetch_oanda_m1.py's default")


def fetch_candles(instrument: str, granularity: str,
                  start: str = DEFAULT_START, end: str = DEFAULT_END,
                  session=None) -> pd.DataFrame:
    """Paginate OANDA candles over [start, end) into a tz-aware UTC OHLC frame.

    OANDA caps a response at 5000 candles, so we walk forward on `from`, using
    the last returned candle time + one granularity step as the next cursor.
    Incomplete (still-forming) candles are dropped — including one would put a
    partial bar in the series and quietly bias every closure test that reads it.
    """
    import requests                                   # local: keeps import cost off test runs

    if session is None:
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {_api_key()}"

    end_ts = pd.Timestamp(end).tz_convert("UTC") if pd.Timestamp(end).tzinfo \
        else pd.Timestamp(end, tz="UTC")
    cur = pd.Timestamp(start)
    cur = cur.tz_convert("UTC") if cur.tzinfo else cur.tz_localize("UTC")

    rows: list[tuple] = []
    while cur < end_ts:
        params = {
            "granularity": granularity,
            "count": MAX_COUNT,
            "price": "M",
            "from": cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
            # Align daily candles to UTC midnight so they share edges with the
            # gold series (which is resampled on a UTC index).
            "alignmentTimezone": "UTC",
            "dailyAlignment": 0,
        }
        r = session.get(f"{HOST}/v3/instruments/{instrument}/candles",
                        params=params, timeout=60)
        r.raise_for_status()
        candles = r.json()["candles"]
        if not candles:
            break
        for cd in candles:
            t = pd.Timestamp(cd["time"])
            if not cd["complete"] or t >= end_ts:
                continue
            m = cd["mid"]
            rows.append((t, float(m["o"]), float(m["h"]),
                         float(m["l"]), float(m["c"])))
        last = pd.Timestamp(candles[-1]["time"])
        if last <= cur:
            break
        cur = last + pd.Timedelta(seconds=1)
        print(f"\r  {instrument} {granularity}: {len(rows):,} bars -> {cur.date()}",
              end="", flush=True)
    print()

    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close"])
    if df.empty:
        return df.set_index("time")
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return (df.drop_duplicates("time").sort_values("time")
              .set_index("time")[["open", "high", "low", "close"]])


# ── verification ──────────────────────────────────────────────────────────────
def verify(df: pd.DataFrame, granularity: str, gold: pd.DataFrame | None = None
           ) -> dict:
    """Bar count, coverage, gap profile, and alignment against the gold series.

    `gold` is the SAME-granularity gold frame. Alignment is reported as the share
    of correlate timestamps that exist in gold and vice versa: SMT compares one
    shared level across two assets, so non-overlapping bars are unusable rows,
    not a cosmetic mismatch.
    """
    out: dict = {"bars": len(df)}
    if df.empty:
        return out
    out["first"] = str(df.index.min())
    out["last"] = str(df.index.max())

    step = pd.Timedelta(hours=1) if granularity == "H1" else pd.Timedelta(days=1)
    deltas = df.index.to_series().diff().dropna()
    out["median_step"] = str(deltas.median())
    # A "gap" is any step of more than 1.5 steps; weekends dominate and are normal.
    gaps = deltas[deltas > step * 1.5]
    out["gaps"] = int(len(gaps))
    out["gap_max"] = str(gaps.max()) if len(gaps) else "none"
    out["gaps_over_3d"] = int((gaps > pd.Timedelta(days=3)).sum())

    if gold is not None and len(gold):
        shared = df.index.intersection(gold.index)
        out["shared_bars"] = len(shared)
        out["share_of_correlate"] = round(len(shared) / len(df), 4)
        out["share_of_gold"] = round(len(shared) / len(gold), 4)
        if len(shared) > 30:
            a = df.loc[shared, "close"].pct_change().dropna()
            b = gold.loc[shared, "close"].pct_change().dropna()
            j = a.index.intersection(b.index)
            out["ret_corr"] = round(float(a.loc[j].corr(b.loc[j])), 4)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and exit without touching the network")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    if args.dry_run:
        for inst, gran, fn in TARGETS:
            print(f"would fetch {inst:9} {gran:2}  {args.start} -> {args.end}"
                  f"  -> {out_dir / fn}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from bars import load_m1, resample                # noqa: E402

    m1 = load_m1()
    gold = {"H1": resample(m1, "1h"), "D": resample(m1, "1D")}

    for inst, gran, fn in TARGETS:
        print(f"fetching {inst} {gran} ...")
        df = fetch_candles(inst, gran, args.start, args.end)
        if df.empty:
            print(f"  !! {inst} {gran}: NO DATA — instrument may not exist on this feed")
            continue
        path = out_dir / fn
        df.to_parquet(path)
        info = verify(df, gran, gold.get(gran))
        print(f"  saved {path}")
        for k, v in info.items():
            print(f"    {k:22} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
