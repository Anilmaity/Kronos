"""Shared baseline book for batch risk_guest_02b (guest risk/no-trade filters).

Baseline = the phase-3 locked bare 1h CISD book (series_open, swing 2/2, max_wait 3,
stop at protected swing, 2R, 10h hold) -- identical to concept_lab.examples.detect_cisd.
Every gate in this batch is a no-trade FILTER, so it is tested as gate_test on this book.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

BASE_PARAMS = {"baseline": "bare CISD", "baseline_tf": "1h", "level_rule": "series_open",
               "swing": "2/2", "max_wait": 3, "rr": 2.0, "max_hold": "10h"}
BASE_SRC = {k: "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked rung-0 config)"
            for k in BASE_PARAMS}
BASE_RULE = ("baseline book: phase-3 bare 1h CISD (series_open level, 2/2 swings, max_wait 3), "
             "decide at confirming 1h close, enter next M1 open, stop at protected swing, 2R, 10h hold")


def cisd_book(m1, tf="1h"):
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "entry_ref", "level", "extreme"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
        "entry_ref": ev["confirm_close"].to_numpy(float),
        "level": ev["level"].to_numpy(float),
        "extreme": ev["extreme_price"].to_numpy(float),
    })
