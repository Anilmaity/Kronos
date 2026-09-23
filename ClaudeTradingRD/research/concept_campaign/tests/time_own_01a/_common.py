"""Shared, pure helpers for batch time_own_01a (TTrades own-voice time concepts).

Baseline book for every clock gate in this batch (declared before any run):
  5m bare CISD, phase-3 locked config (series_open, 2/2 swings, max_wait 3, min_series 1),
  decided at the confirming 5m bar's close, entry next M1 open, stop = protected swing,
  target 2R, time exit 10 entry-TF bars = 50 min. 5m is the finest phase-3 locked stack and
  is one of the LTF execution frames the corpus names for these windows (15m/5m/3m).
Every helper builds from the M1 frame it is given, so probe_lookahead sees exactly what
the detectors read. No harness edits.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

COMMON = __file__
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
BASE_TF = "5min"
BASE_RR = 2.0
BASE_MAX_HOLD = "50min"

BASE_PARAMS = {"baseline_tf": BASE_TF, "cisd": CISD_KW, "rr": BASE_RR,
               "max_hold": BASE_MAX_HOLD}
BASE_SRC = {
    "baseline_tf": "declared-before-run: 5m CISD book = finest phase-3 locked stack; corpus "
                   "LTF for the NY window is 15m/5m (entry-time-window timeframes.ltf)",
    "cisd": "phase3: locked CISD config (conjunction_preregistration 1.8-1.13: series_open, "
            "2/2, max_wait 3)",
    "rr": "phase3: 2R target (conjunction_preregistration locked config)",
    "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13) = 50 min on 5m",
}


def cisd5(m1):
    """Bare 5m CISD events (no gate)."""
    b = cl.build_bars(m1, BASE_TF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if len(b) < 20:
        return pd.DataFrame(columns=cols)
    ev = cisd_events(b[["open", "high", "low", "close"]], **CISD_KW)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float), "rr": BASE_RR})
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def base_cached():
    """The full-data baseline frame, cached once for the whole batch."""
    return cl.cache_frame("time_own_01a_cisd5_base", lambda: cisd5(cl.load_m1()),
                          script=COMMON)


def window_mask(times, windows):
    """True when the NY wall-clock minute of `times` is inside any [start, end) window."""
    m = np.zeros(len(times), bool)
    for a, z in windows:
        m |= cl.in_window(pd.DatetimeIndex(times), a, z)
    return m
