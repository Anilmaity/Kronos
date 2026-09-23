"""mmxm-twitter-model — The MMXM Trader's "Twitter Model" (taught by TTrades). CONTESTED:
two different five-condition lists under one name.

Reading a — the earlier "Next Day Model" recording (klaiq36QnEM), a timing/selection filter:
  * the anticipated HTF level = an unfilled DAILY fair value gap (the first example type
    named; the level type is untyped in the corpus), formed within the last 20 days;
  * level day D: D trades into the gap and reacts — closes back outside it on the near side
    (bearish FVG above: high >= gap low, close < gap low) -> bias away from it;
  * trade the NEXT session only, never Monday; New York session only (08:30-12:00 NY);
  * execute on 15m: the first 15m CISD in the bias direction inside the window (series_open,
    2/2, max_wait 3); stop at its protected swing; 2R; 150 min hold.
Reading b — the canonical re-recording (WwmS47Gb3M0), external -> internal liquidity:
  * short: the previous day's high is raided (the CISD's swing extreme, in today's trading
    day, is above PDH); a bearish 15m CISD (the stated MSS substitute) confirms;
  * SMT: silver did NOT take its own previous-day high (silver 1h bars closed by the
    decision; only 1h silver exists locally, so this is an hourly SMT proxy);
  * entry only ABOVE the midnight open for shorts (below for longs); no trade before
    midnight (midnight open not yet printed);
  * target = the nearest unmitigated 1h bullish FVG below the entry (its top edge), formed
    within the last 120 hourly bars; none -> no trade;
  * stop at the raid extreme (protected swing); 150 min hold. Long side mirrored.
trade_test vs matched random entry, claim '+'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                            # noqa: E402
from detectors.cisd import cisd_events                              # noqa: E402
from detectors.primitives import fair_value_gaps                    # noqa: E402

CID = "mmxm-twitter-model"
TF = "15min"
MAX_HOLD = "150min"
NY = ("08:30", "12:00")
DFVG_LOOKBACK = 20
HFVG_LOOKBACK = 120
XAG_PATH = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet"
_XAG = {}


def _silver():
    if "d" not in _XAG:
        x = pd.read_parquet(XAG_PATH).sort_index()
        x.index = pd.DatetimeIndex(x.index).tz_convert("UTC")
        x["close_time"] = x.index + pd.Timedelta(hours=1)
        x["td"] = cl.trading_day(x.index)
        dh = x.groupby("td")["high"].max()
        dl = x.groupby("td")["low"].min()
        x["pdh"] = x["td"].map(dh.shift(1))
        x["pdl"] = x["td"].map(dl.shift(1))
        _XAG["d"] = x
    return _XAG["d"]


def _cisd15(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3)
    if ev.empty:
        return b, ev, pd.DatetimeIndex([], tz="UTC")
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return b, ev, close


# ── reading a ────────────────────────────────────────────────────────────────
def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    d = cl.build_bars(m1, "1D")
    med = float(np.median(d["n_m1"])) if len(d) else 0
    d = d[d["n_m1"] >= 0.5 * med]
    if len(d) < 5:
        return pd.DataFrame(columns=cols)
    f = fair_value_gaps(d[["open", "high", "low", "close"]])
    H, L, C = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    bias = {}                                   # trading_day of level day -> direction
    tdays = pd.DatetimeIndex(d["trading_day"])
    for k in range(3, len(d)):
        sig = 0
        for g in range(max(2, k - DFVG_LOOKBACK), k):   # gap stamped on bar g, known at its close
            lo_, hi_ = f["gap_low"].iloc[g], f["gap_high"].iloc[g]
            if not np.isfinite(lo_):
                continue
            between = slice(g + 1, k)
            if f["bearish_fvg"].iloc[g]:
                if (H[between] >= lo_).any():        # already traded into -> not unfilled
                    continue
                if H[k] >= lo_ and C[k] < lo_:
                    sig = -1 if sig in (0, -1) else 99
            elif f["bullish_fvg"].iloc[g]:
                if (L[between] <= hi_).any():
                    continue
                if L[k] <= hi_ and C[k] > hi_:
                    sig = 1 if sig in (0, 1) else 99
        if sig in (-1, 1):
            bias[tdays[k]] = (sig, pd.Timestamp(d["close_time"].iloc[k]))
    b, ev, close = _cisd15(m1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})
    out = out[cl.in_window(out["decision_time"], *NY)]
    ny = cl.to_ny(out["decision_time"])
    out = out[np.asarray(ny.dayofweek != 0)]          # skip Monday
    td = cl.trading_day(out["decision_time"])
    # the level day is the PREVIOUS real trading day
    pos = np.searchsorted(tdays.values, td.values, side="left") - 1
    rows = []
    seen = set()
    for (i, r), p, t in zip(out.iterrows(), pos, td):
        if p < 0 or tdays[p] >= t:
            continue
        got = bias.get(tdays[p])
        if got is None or got[0] != r["direction"] or t in seen:
            continue
        seen.add(t)                                   # first qualifying trade per day
        rows.append(r.to_dict())
    return pd.DataFrame(rows, columns=cols)


# ── reading b ────────────────────────────────────────────────────────────────
def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    b, ev, close = _cisd15(m1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    bull = (ev["direction"] == "bullish").to_numpy()
    ext = ev["extreme_price"].to_numpy(float)
    cc = ev["confirm_close"].to_numpy(float)
    ph = cl.prior_hilo(close, "1D", m1=m1, min_coverage=0.5)
    same_day = np.asarray(cl.trading_day(pd.DatetimeIndex(ev["extreme_time"]))
                          == cl.trading_day(close))
    raid = np.where(bull, ext < ph["low"].to_numpy(), ext > ph["high"].to_numpy())
    mo = cl.open_at(close, "00:00", m1=m1)["price"].to_numpy(float)
    side_ok = np.where(bull, cc < mo, cc > mo)
    keep = np.flatnonzero(same_day & raid & np.isfinite(mo) & side_ok)
    if not len(keep):
        return pd.DataFrame(columns=cols)
    h1 = cl.build_bars(m1, "1h")
    fv = fair_value_gaps(h1[["open", "high", "low", "close"]])
    fv["avail"] = pd.DatetimeIndex(h1["close_time"])
    fv = fv[fv["bullish_fvg"] | fv["bearish_fvg"]]
    fv_av = fv["avail"].values.astype("datetime64[ns]").astype(np.int64)
    h1_close = pd.DatetimeIndex(h1["close_time"]).as_unit("ns").asi8
    tn = m1.index.as_unit("ns").asi8
    H, L = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    xag = _silver()
    x_ct = pd.DatetimeIndex(xag["close_time"]).as_unit("ns").asi8
    x_td = xag["td"].values
    x_h, x_l = xag["high"].to_numpy(float), xag["low"].to_numpy(float)
    x_pdh, x_pdl = xag["pdh"].to_numpy(float), xag["pdl"].to_numpy(float)
    rows = []
    for k in keep:
        t = close[k].value
        tday = cl.trading_day(pd.DatetimeIndex([close[k]]))[0]
        # SMT: silver 1h bars of the same trading day closed by t
        xi = np.searchsorted(x_ct, t, side="right")
        xs = np.flatnonzero(x_td[:xi] == np.datetime64(tday))
        if not len(xs):
            continue
        if bull[k]:
            if not (x_l[xs].min() >= x_pdl[xs[0]]):     # silver held its PDL
                continue
        else:
            if not (x_h[xs].max() <= x_pdh[xs[0]]):     # silver held its PDH
                continue
        # target: nearest unmitigated 1h FVG on the opposite side, formed within lookback
        n_av = np.searchsorted(h1_close, t, side="right")
        oldest = h1_close[max(0, n_av - HFVG_LOOKBACK)] if n_av else t
        sel = np.flatnonzero((fv_av <= t) & (fv_av >= oldest))
        best = None
        for g in sel[::-1]:
            row = fv.iloc[g]
            if bull[k]:
                if not row["bearish_fvg"] or not (row["gap_low"] > cc[k]):
                    continue
                edge = row["gap_low"]
            else:
                if not row["bullish_fvg"] or not (row["gap_high"] < cc[k]):
                    continue
                edge = row["gap_high"]
            i0 = np.searchsorted(tn, fv_av[g], side="left")
            i1 = np.searchsorted(tn, t, side="left")
            if i1 > i0:
                if bull[k] and H[i0:i1].max() >= edge:
                    continue
                if (not bull[k]) and L[i0:i1].min() <= edge:
                    continue
            if best is None or (abs(edge - cc[k]) < abs(best - cc[k])):
                best = edge
        if best is None:
            continue
        rows.append({"decision_time": close[k], "available_at": close[k],
                     "direction": 1 if bull[k] else -1, "stop_px": ext[k],
                     "target_px": float(best)})
    return pd.DataFrame(rows, columns=cols)


READ = {
    "a": (detect_a, {"rules": [
        "HTF level = unfilled daily FVG formed in the last 20 daily bars; level day trades into "
        "it and closes back on the near side -> bias away from it for the next session",
        "next session only, not Monday; decisions inside NY 08:30-12:00",
        "first 15m CISD (series_open, 2/2, max_wait 3) in the bias direction that day; stop at "
        "the protected swing; 2R; exit after 150 min"],
        "params": {"level": "daily FVG", "dfvg_lookback": DFVG_LOOKBACK, "reaction":
                   "close back outside on the near side", "skip_monday": True,
                   "ny_window": "08:30-12:00", "tf": TF, "entry": "first 15m CISD in bias",
                   "rr": 2.0, "max_hold": MAX_HOLD}},
        {"level": "corpus: klaiq36QnEM — 'trading the day after your anticipated higher time "
                  "frame level is hit'; daily FVG is the first example type (declared-before-run "
                  "choice among FVG/OB/PD array)",
         "dfvg_lookback": "declared-before-run: gaps formed within the last 20 daily bars",
         "reaction": "declared-before-run: 'a reaction off the level' = the level day closes "
                     "back outside the gap on the near side",
         "skip_monday": "corpus: klaiq36QnEM 'I want to reiterate skipping Monday'",
         "ny_window": "method_spec: §2.5 New York a.m. 08:30-12:00",
         "tf": "corpus: klaiq36QnEM 'executing on the 15-minute chart'",
         "entry": "phase3: rung-0 CISD config as the 15m execution trigger (declared)",
         "rr": "method_spec: §5.3 '2R is the floor'",
         "max_hold": "phase3: 10 entry-TF bars (§1.13)"}),
    "b": (detect_b, {"rules": [
        "short: 15m bearish CISD whose swing extreme (same trading day) is above the previous "
        "day's high; long mirrored on PDL",
        "SMT: silver's 1h bars of the same trading day closed by the decision did not take "
        "silver's own PDH (PDL for longs)",
        "short only if the CISD close is above the midnight open (long: below); no trade "
        "before midnight",
        "target = top (bottom) edge of the nearest unmitigated 1h bullish (bearish) FVG "
        "below (above) the entry, formed within 120 hourly bars; none -> no trade",
        "stop at the raid extreme; exit after 150 min"],
        "params": {"tf": TF, "raid": "PDH/PDL (prior_hilo, min_coverage 0.5)",
                   "mss": "15m CISD series_open 2/2 max_wait 3", "smt": "silver 1h, PDH/PDL held",
                   "midnight_filter": True, "target": "nearest unmitigated 1h FVG edge",
                   "hfvg_lookback": HFVG_LOOKBACK, "max_hold": MAX_HOLD}},
        {"tf": "corpus: WwmS47Gb3M0 — 15-minute structure shift",
         "raid": "corpus: WwmS47Gb3M0 — previous day high raided (short) / low (long)",
         "mss": "corpus: WwmS47Gb3M0 'although the model says a market structure shift I will "
                "also look for an inversion' (change in state of delivery permitted); phase3 "
                "CISD config",
         "smt": "corpus: WwmS47Gb3M0 — SMT required; silver is the stated correlate for gold; "
                "declared-before-run: 1h silver is the finest available, so an hourly SMT proxy",
         "midnight_filter": "corpus: WwmS47Gb3M0 'looking to only short above midnight open and "
                            "then vice versa for Longs'",
         "target": "corpus: WwmS47Gb3M0 'moving from external liquidity to internal liquidity "
                   "on a smaller time frame' — hourly FVG target; nearest unmitigated = "
                   "'prefer the gap that has not already been reached into'",
         "hfvg_lookback": "declared-before-run: 120 hourly bars (~5 sessions)",
         "max_hold": "phase3: 10 entry-TF bars (§1.13)"}),
}

if __name__ == "__main__":
    for rd in (sys.argv[1:] or ["a", "b"]):
        fn, op, src = READ[rd]
        ev = cl.cache_frame(f"{CID}_{rd}_v1", lambda: fn(cl.load_m1()))
        print(rd, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(fn, ev, lookback="30D" if rd == "a" else "10D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, max_hold=MAX_HOLD)
        for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "ties", "ctrl_overlap", "dropped"):
            print(" ", k, res.get(k))
        print(cl.write_result(CID, rd, res, operationalization=op, params_source=src,
                              script=__file__, probe=probe,
                              notes=("Silver 1h (m3_scalper/xag_h1_full.parquet) read only "
                                     "through bars closed by the decision time; the probe "
                                     "truncates gold only." if rd == "b" else "")))
