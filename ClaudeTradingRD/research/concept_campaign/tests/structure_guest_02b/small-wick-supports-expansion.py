"""small-wick-supports-expansion (guest: GxTradez) -> gate_test.

Claim: a candle that closed from a key level with a SMALL opposing wick ("reversal into
expansion candle") supports expansion and is tradeable; a LARGE opposing wick ("reversal
candle") does not support expansion (on the 4-hour: do not trade it, wait for the next
candle). claim '+' = small-wick entries beat large-wick entries, control-adjusted.

Baseline book (declared before the run): 4H candles (forex grid) that closed FROM a key
level = swept the previous 4H candle's low (high) and closed back above (below) it, with a
body in the reversal direction (close > open for a long). One side only (no outside bars
sweeping both). Entry: next M1 open after the candle closes; stop: the candle's swept
extreme; target 2R; max_hold 40h (10 x 4H bars).
Gate: opposing_run / body <= 1.0 (opposing run = open -> extreme against the trade,
threshold_fits grade A crossover), known at the candle's close.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TF = "4h"
GRID = "forex"
CUT = 1.0
RR = 2.0
MAX_HOLD = "40h"
MIN_M1 = 60
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "small_wick", "wick_ratio"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF, grid4h=GRID)
    b = b[b["n_m1"] >= MIN_M1]
    if len(b) < 3:
        return pd.DataFrame(columns=COLS)
    o, h, l, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    sw_lo = (l < pl) & (c >= pl)
    sw_hi = (h > ph) & (c <= ph)
    long_ = sw_lo & ~sw_hi & (c > o)
    short = sw_hi & ~sw_lo & (c < o)
    sel = long_ | short
    ct = pd.DatetimeIndex(b["close_time"])
    # decision at the nominal close_time: every M1 bar of the candle starts before it,
    # so any event the probe compares (decision <= cut) is built from a complete candle
    body = np.abs(c - o)
    opp = np.where(long_, o - l, h - o)
    ratio = np.where(body > 0, opp / np.where(body > 0, body, 1), np.inf)
    idx = np.flatnonzero(sel)
    ev = pd.DataFrame({
        "decision_time": ct[idx], "available_at": ct[idx],
        "direction": np.where(long_[idx], 1, -1),
        "stop_px": np.where(long_[idx], l[idx], h[idx]),
        "rr": RR,
        "small_wick": ratio[idx] <= CUT,
        "wick_ratio": ratio[idx],
    })
    return ev.reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"swse_{TF}_{GRID}_cut{CUT}_min{MIN_M1}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.small_wick.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "small_wick", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "4H forex-grid candles that swept the prior 4H low (high) and closed back inside, "
        "reversal-direction body, one side only",
        "entry next M1 open after the close; stop = candle's swept extreme; 2R; 40h hold",
        "gate: opposing run (open->extreme against trade) / body <= 1.0 = small wick",
        "gate_test small vs large, control-adjusted R"],
        "params": {"tf": TF, "grid4h": GRID, "cut": CUT, "rr": RR, "max_hold": MAX_HOLD,
                   "min_m1": MIN_M1}}
    src = {"tf": "corpus: J_EeS2_2CAM - the 4-hour is the timeframe where large-wick candles are not traded",
           "grid4h": "session_window_fit: forex grid for gold (carried as knob, phase3)",
           "cut": "threshold_fits: small wick opposing_run/body <= 1.0 (grade A)",
           "rr": "declared-before-run: no target stated; 2R",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "min_m1": "declared-before-run: skip stub 4H bars (<60 M1 bars)"}
    p = cl.write_result("small-wick-supports-expansion", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Key level = the prior 4H candle's extreme (C2-style sweep); the daily "
                              "'reduced targets' branch is not tested.")
    print(p)
