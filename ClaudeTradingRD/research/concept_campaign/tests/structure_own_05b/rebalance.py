"""rebalance -> reading a: trade_test (post-creation rebalance -> reversal);
              reading b: rate_test (pre-creation rebalance on the daily).

Source opYUBJ8IFgg: "there are two ways a fair value gap is rebalanced - one before it is
created and one after it is created"; "after you rebalance something there's not an
imbalance there so price tends to reverse"; "it came down balanced this out made sure there
was no fair value gap created"; "this kind of rebalance I more focus for on the daily chart".
The two cases make distinct claims, so each is a reading.

Reading a (trade_test, claim '+'): when price comes back and fully closes a fair value gap,
price reverses there. 1h three-bar FVGs; full fill = first M1 touch of the gap's far edge
within 5 days of formation (without a prior M1 touch? no - the first far-edge touch). Trade
the reversal = the gap's own direction (a bullish gap filled from above -> long), decided at
the touch minute's close, entered next M1 open; stop = one gap height beyond the far edge;
2R; hold 10h. A touch minute that also reaches the stop is not entered.

Reading b (rate_test, claim '+'): on the daily, a candle that opens leaving a would-be gap
against C1's extreme (C3 open above C1 high, bullish; mirrored) trades back to C1's extreme
BEFORE continuing through C2's extreme, more often than a geometry-matched null race (same
two distances from price, same bar horizon). Only days whose open sits inside C2's range on
the continuation side (open < C2 high, bullish) - otherwise there is no race.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from detectors.primitives import fair_value_gaps  # noqa: E402
from _common import m1_arrays, from_ns, ONE_MIN, show  # noqa: E402

CID = "rebalance"
TF_A = "1h"
WIN_A = pd.Timedelta("5D")
RR = 2.0
HOLD_A = "10h"
MIN_BARS = 600
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "rr", "gap_id"]
COLS_B = ["decision_time", "available_at", "direction", "lvl_rebal", "lvl_cont"]


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF_A)
    if len(b) < 5:
        return pd.DataFrame(columns=COLS_A)
    f = fair_value_gaps(b[["open", "high", "low", "close"]])
    isbull = f["bullish_fvg"].to_numpy(bool)
    isbear = f["bearish_fvg"].to_numpy(bool)
    gl, gh = f["gap_low"].to_numpy(float), f["gap_high"].to_numpy(float)
    ct = b["close_time"].values.astype("datetime64[ns]").astype(np.int64)
    mt, MH, ML = m1_arrays(m1)
    out = []
    for i in np.flatnonzero(isbull | isbear):
        bull = bool(isbull[i])
        size = gh[i] - gl[i]
        if not size > 0:
            continue
        a = np.searchsorted(mt, ct[i], "left")
        e = np.searchsorted(mt, ct[i] + WIN_A.value, "left")
        if a >= e:
            continue
        far = gl[i] if bull else gh[i]
        stop = far - size if bull else far + size
        hit = (ML[a:e] <= far) if bull else (MH[a:e] >= far)
        if not hit.any():
            continue
        k = int(np.argmax(hit))
        if (ML[a + k] <= stop) if bull else (MH[a + k] >= stop):
            continue
        out.append((int(mt[a + k]), 1 if bull else -1, stop, int(ct[i])))
    if not out:
        return pd.DataFrame(columns=COLS_A)
    o = pd.DataFrame(out, columns=["t", "direction", "stop_px", "gap_id"])
    dec = from_ns(o["t"].to_numpy()) + ONE_MIN
    ev = pd.DataFrame({"decision_time": dec, "available_at": dec,
                       "direction": o["direction"].astype(int).to_numpy(),
                       "stop_px": o["stop_px"].to_numpy(float), "rr": RR,
                       "gap_id": o["gap_id"].astype(np.int64).to_numpy()})
    return ev.sort_values(["decision_time", "gap_id"]).reset_index(drop=True)[COLS_A]


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    if len(d) < 4:
        return pd.DataFrame(columns=COLS_B)
    o, h, l = (d[x].to_numpy(float) for x in ("open", "high", "low"))
    real = np.flatnonzero(d["n_m1"].to_numpy() >= MIN_BARS)   # completed-day stub filter
    start = pd.DatetimeIndex(d["first_m1"])
    rows = []
    for k in range(2, len(d)):
        j = np.searchsorted(real, k, "left")                  # real days strictly before k
        if j < 2:
            continue
        c2, c1 = real[j - 1], real[j - 2]
        if o[k] > h[c1] and o[k] < h[c2]:                     # would-be bullish gap vs C1 high
            rows.append((k, 1, h[c1], h[c2]))
        elif o[k] < l[c1] and o[k] > l[c2]:                   # would-be bearish gap vs C1 low
            rows.append((k, -1, l[c1], l[c2]))
    if not rows:
        return pd.DataFrame(columns=COLS_B)
    r = pd.DataFrame(rows, columns=["k", "direction", "lvl_rebal", "lvl_cont"])
    # decide at C3's first M1 open (the open is then known): first_m1 + 1 min
    dec = pd.DatetimeIndex(start[r["k"].to_numpy()]) + ONE_MIN
    av = dec
    return pd.DataFrame({"decision_time": dec, "available_at": av,
                         "direction": r["direction"].to_numpy(int),
                         "lvl_rebal": r["lvl_rebal"].to_numpy(float),
                         "lvl_cont": r["lvl_cont"].to_numpy(float)}).reset_index(drop=True)


def race(times, lvl_a, side_a, lvl_b, side_b, hb):
    """1 where lvl_a is touched strictly before lvl_b (or lvl_a only), within hb bars."""
    ta = cl.touch(times, lvl_a, side_a, horizon_bars=hb)
    tb = cl.touch(times, lvl_b, side_b, horizon_bars=hb)
    ha, hbt = ta["hit"].to_numpy(), tb["hit"].to_numpy()
    at, bt = ta["hit_time"].to_numpy(), tb["hit_time"].to_numpy()
    return (ha & (~hbt | (at < bt))).astype(float)


def run_a():
    ev = cl.cache_frame(f"{CID}_a_{TF_A}_5D_rr2", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=HOLD_A, cluster="gap_id")
    print("reading a"); show(res)
    op = {"rules": ["1h three-bar FVGs known at the third bar's close; eligible 5 days",
                    "post-creation rebalance = first M1 touch of the gap's far edge (full fill)",
                    "trade the reversal = the gap's direction; decide at the touch minute's "
                    "close, next M1 open; stop = one gap height beyond the far edge; skip if "
                    "the touch minute also hits it; 2R; hold 10h"],
          "params": {"tf": TF_A, "window": "5D", "fill": "wick to far edge",
                     "stop": "1 gap height beyond far edge", "rr": RR, "max_hold": HOLD_A}}
    src = {"tf": "declared-before-run: post-creation form has no stated timeframe (fractal); "
                 "1h between the htf 1D and ltf 5m/1m",
           "window": "declared-before-run: how long a gap stays eligible is not stated; 5D",
           "fill": "corpus: opYUBJ8IFgg 'price comes back and closes the fair value gap' - "
                   "examples show full closure (ambiguity notes full fill vs CE)",
           "stop": "declared-before-run: no stop given; one gap height beyond the far edge",
           "rr": "phase3: 2R primary target", "max_hold": "phase3: 10 entry-TF bars"}
    print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Post-creation case: 'price tends to reverse' after a full "
                                "fill; the reversal is traded in the gap's original direction."))


def run_b():
    ev = cl.cache_frame(f"{CID}_b_daily", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    print("probe", probe.get("passed"))
    mkt = cl.get_market()
    dall = cl.bars("1D")
    fm = cl.data.utc_ns(pd.DatetimeIndex(dall["first_m1"]))
    t = pd.DatetimeIndex(ev["decision_time"])
    kk = np.searchsorted(fm, cl.data.utc_ns(t - ONE_MIN), side="left")
    hb = dall["n_m1"].to_numpy()[kk].astype(np.int64) - 1        # rest of C3, in bars
    up = ev["direction"].to_numpy() > 0
    p0 = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    da = ev["lvl_rebal"].to_numpy() - p0
    db = ev["lvl_cont"].to_numpy() - p0

    def outcome(times, px, u, da_, db_, hb_):
        res_ = np.zeros(len(times))
        for sgn, sel in ((1, u), (-1, ~u)):
            if sel.any():
                sa, sb = ("below", "above") if sgn > 0 else ("above", "below")
                res_[sel] = race(times[sel], (px + da_)[sel], sa, (px + db_)[sel], sb,
                                 hb_[sel])
        return res_

    obs = outcome(t, p0, up, da, db, hb)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        tt = tk[ok]
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tt), len(mkt.o) - 1)]
        out[ok] = outcome(tt, px, up[ok], da[ok], db[ok], hb[ok])
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null_fn=null_fn, predictors=ev, outcome_horizon="1D")
    print("reading b"); show(res)
    op = {"rules": ["daily candles on the 18:00 NY trading day; C1/C2 = the last two completed sessions with >= 600 M1 bars",
                    "C3 opens beyond C1's extreme (would-be gap) but inside C2's range on the "
                    "continuation side",
                    "decide at C3's first M1 bar close; hit = C1's extreme touched strictly "
                    "before C2's extreme within the rest of C3 (M1 bars)",
                    "null = the same race (same two signed distances, same bar horizon) from "
                    "5 random moments within +/-30 days"],
          "params": {"min_bars": MIN_BARS, "day_open_hour": 18,
                     "continuation_level": "C2 extreme", "horizon": "rest of C3"}}
    src = {"min_bars": "declared-before-run: README trap 6 stub sessions",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "continuation_level": "declared-before-run: 'only then continues' - continuing = "
                                 "trading through C2's extreme (the three-candle frame)",
           "horizon": "corpus: opYUBJ8IFgg 'the daily candle opens, comes down and "
                      "rebalances, then moves higher' - within the same daily candle"}
    print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Pre-creation case on the daily, as a race vs a matched null; "
                                "'the majority of candles do this' is a base-rate claim, so "
                                "the question asked is whether the would-be gap is a magnet "
                                "beyond geometry."))


if __name__ == "__main__":
    # reading a was run once and written; reading b's first probe caught a detector bug
    # (the stub filter read C3's own bar count) BEFORE any b result existed, so only b was
    # re-run after the fix. Run a subset with: python rebalance.py b
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run_a()
    if "b" in which:
        run_b()

