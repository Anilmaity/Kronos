"""strat-timeframe-continuity (guest: Alex's Options, TheSTRAT) -> gate_test.

"continuity_up := the open higher-timeframe candle is currently trading above its open price";
"do not take a large counter-trend position against a fresh higher-timeframe candle whose
continuity runs the other way". Declared before the first run:
  * HTF = the calendar month (the guest's headline 'new monthly continuity'); month open =
    open of the month's first M1 bar (build_bars '1M'); state read at the decision from the
    signal bar's close vs that open (known: the open is the month's first print).
  * Baseline book (a neutral two-sided swing book): the phase-3 rung-0 CISD on 4h bars
    (forex grid; series_open, max_wait 3, swings 2/2), entry after the confirming bar's close,
    stop = protected swing, 2R, hold 10 bars = 40h of trading bars (hold_basis="bars").
    4h is chosen over 1h because the prohibition is about 'large' moves.
  * Gate (claim '+'): the trade agrees with monthly continuity (long while the month trades
    above its open, short while below). Complement = trades against continuity.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CID = "strat-timeframe-continuity"
TF = "4h"
MAX_HOLD = "40h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "with_month"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF, grid4h="forex")
    mo = cl.build_bars(m1, "1M")
    if len(b) < 10 or not len(mo):
        return pd.DataFrame(columns=COLS)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=COLS)
    close_t = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    start_t = pd.DatetimeIndex(ev["confirm_time"])
    mpos = np.searchsorted(mo.index.values, start_t.values, side="right") - 1
    ok = mpos >= 0
    mopen = np.where(ok, mo["open"].to_numpy(float)[np.clip(mpos, 0, None)], np.nan)
    d = np.where(ev["direction"].to_numpy() == "bullish", 1, -1)
    cc = ev["confirm_close"].to_numpy(float)
    up = cc > mopen
    with_m = np.where(d == 1, up, ~up)
    out = pd.DataFrame({"decision_time": close_t, "available_at": close_t, "direction": d,
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                        "with_month": with_m.astype(bool)})
    out = out[ok].sort_values(["decision_time", "direction"]).reset_index(drop=True)
    return out[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame("strat_tfc_month_cisd4h", lambda: detect(cl.load_m1()))
    print(len(ev), ev["with_month"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "with_month", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       hold_basis="bars")
    for k in ("n", "n_complement", "gate_firing_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "halves"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "baseline: 4h CISD rung-0 (forex grid, series_open, max_wait 3, swings 2/2); stop protected swing; 2R; hold 40h of bars",
        "monthly continuity: signal bar close vs the open of the current calendar month (first M1 of the month)",
        "gate: long while month trades above its open / short while below; complement: against continuity"],
        "params": {"baseline_tf": TF, "grid4h": "forex", "cisd_max_wait": 3, "rr": 2.0, "max_hold": MAX_HOLD,
                   "hold_basis": "bars", "htf": "1M"}}
    src = {"baseline_tf": "declared-before-run: 4h CISD as a neutral two-sided swing-sized book ('large move')",
           "grid4h": "session_window_fit: forex grid for gold (carried as a knob)",
           "cisd_max_wait": "phase3: rung-0 CISD (series_open, max_wait 3, swings 2/2)",
           "rr": "phase3: 2R target (rung-0)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "hold_basis": "declared-before-run: 40h spans weekends from 4h closes; trading-time hold",
           "htf": "corpus: V8P6lNIisvc 'new monthly continuity, which just means new monthly open'"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Monthly continuity only; quarterly/6M/12M continuity and the 'fresh month' "
                              "qualifier are not separately tested.")
    print(p)
