"""Shared baseline for batch risk_own_02b (my own code; the harness is untouched).

Baseline entry book = the campaign's canonical rung-0 CISD book (phase-3 locked config,
meta/conjunction_preregistration.md §1.8-1.13): series_open level, 2/2 swings,
max_wait 3, min_series 1; decide at the confirming bar's close; stop at the protected
swing; enter the next M1 open; hold 10 entry-TF bars. Pure in its M1 input.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402,F401
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

PHASE3_SRC = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked rung-0 config)"
HOLD_SRC = "phase3: 10 entry-TF bars (§1.13)"


def cisd_book(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "confirm_close"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close,
        "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "confirm_close": ev["confirm_close"].to_numpy(float),
    })
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


def show(res: dict) -> None:
    keys = ("test_type", "claim", "n", "n_gated", "n_complement", "avg_R", "win_rate",
            "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
            "verdict_detail", "ctrl_overlap", "ties", "exposure_bars", "gate_rate", "halves")
    for k in keys:
        if res.get(k) is not None:
            print(f"  {k:15s} {res[k]}")
