"""four-hour-wick-positioning — Trader Kane: inside the forming 4H candle, the hourly expands,
price retraces, he is filled at 50% of the move and holds toward the 4H candle's close.

Test: trade_test (claim '+': beats a matched random entry with the same stop distance and
the same hold).

Operationalisation (bullish; bearish mirrored):
  hourly expansion = a completed 1h bar that CLOSES above the prior 1h bar's high (structural
  displacement gate) with a small opposing wick: (open - low) <= (close - open) (small-wick cut 1.0).
  The 1h bar must lie inside a 4H bar (forex grid) that is still forming at its close.
  entry = the first M1 bar after the 1h close, still inside that 4H bar, whose low trades at or
  below 50% of the 1h bar's range; decide at that M1 bar's close, enter next M1 open.
  stop = the expansion bar's low (not stated in the source; declared).
  exit = the 4H candle's close (time exit; no price target).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "four-hour-wick-positioning"
WICK_CUT = 1.0
GRID = "forex"


def detect(m1):
    h1 = cl.build_bars(m1, "1h")
    h4 = cl.build_bars(m1, "4h", grid4h=GRID)
    o, h, l, c = (h1[x].to_numpy() for x in ("open", "high", "low", "close"))
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    bull = (c > ph) & ((o - l) <= WICK_CUT * (c - o)) & (c > o)
    bear = (c < pl) & ((h - o) <= WICK_CUT * (o - c)) & (c < o)
    starts = h1.index
    ct1 = pd.DatetimeIndex(h1["close_time"])
    k4 = np.searchsorted(h4.index.values, starts.values, side="right") - 1
    ok4 = k4 >= 0
    ct4 = pd.DatetimeIndex(h4["close_time"])
    m_t = m1.index.values
    m_lo, m_hi = m1["low"].to_numpy(), m1["high"].to_numpy()
    rows = []
    for i in np.where((bull | bear) & ok4)[0]:
        c4 = ct4[k4[i]]
        if not (ct1[i] < c4) or starts[i] < h4.index[k4[i]]:
            continue
        mid = (h[i] + l[i]) / 2.0
        a = np.searchsorted(m_t, ct1[i].to_datetime64())          # first M1 starting >= 1h close
        b = np.searchsorted(m_t, (c4 - pd.Timedelta("1min")).to_datetime64(), side="right")
        if a >= b:
            continue
        if bull[i]:
            hit = np.where(m_lo[a:b] <= mid)[0]
            d, stop = 1, l[i]
        else:
            hit = np.where(m_hi[a:b] >= mid)[0]
            d, stop = -1, h[i]
        if not len(hit):
            continue
        dec = pd.Timestamp(m_t[a + hit[0]]).tz_localize("UTC") + pd.Timedelta("1min")
        hold = c4 - dec
        if hold <= pd.Timedelta(0):
            continue
        rows.append((dec, d, stop, hold))
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "max_hold"])
    df = df.sort_values(["decision_time", "direction"]).drop_duplicates(
        ["decision_time", "direction"]).reset_index(drop=True)
    return pd.DataFrame({"decision_time": df.decision_time, "available_at": df.decision_time,
                         "direction": df.direction.astype(int), "stop_px": df.stop_px,
                         "rr": np.nan, "max_hold": df.max_hold})


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_w{WICK_CUT}_{GRID}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict(), ev.max_hold.describe())
    if "--dry" in sys.argv:
        print(ev.head()); raise SystemExit
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.trade_test(ev, claim="+")
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "hourly expansion = completed 1h bar closing beyond the prior 1h bar's extreme with opposing "
        "wick <= body, inside a 4H bar (forex grid) still forming at its close",
        "entry = first M1 after the 1h close and before the 4H close trading to 50% of the 1h range; "
        "decide at that M1 close, enter next M1 open, in the expansion direction",
        "stop = the expansion bar's far extreme (100% retrace); no target; exit at the 4H close"],
        "params": {"small_wick_cut": WICK_CUT, "grid4h": GRID, "retrace": 0.5,
                   "stop": "expansion bar extreme", "exit": "4H candle close"}}
    src = {"small_wick_cut": "threshold_fits: small wick opposing_run/|body| <= 1.0 (grade A); displacement structural gate = close beyond reference",
           "grid4h": "session_window_fit: forex 4H grid for gold (carried as a knob)",
           "retrace": "corpus: 1wKfc2gN4xg 'filled on that retrace at 50% of the move' (concept yaml)",
           "stop": "declared-before-run: no stop stated in the interview; the origin of the expansion leg",
           "exit": "corpus: 1wKfc2gN4xg execution target 'the close of the 4-hour / hourly candle'"}
    notes = ("The 'invert something inside the wick' trigger and the shallow-wick switch are undefined "
             "in the source and are not modelled; the 10:00 overlap is a preference, not a rule. "
             "This tests the stated core: buy the 50% retrace of the hourly expansion inside the "
             "forming 4H candle and hold to its close.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, notes=notes, probe=probe)
    print(p)
