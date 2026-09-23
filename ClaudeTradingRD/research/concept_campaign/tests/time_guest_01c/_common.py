"""Shared helpers for batch time_guest_01c (pure functions of the M1 input).

Every helper builds its bars FROM the M1 frame it is given so detectors that use
them stay probe-able by cl.probe_lookahead.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

PHASE3 = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked bare-CISD config)"


def cisd_book(m1: pd.DataFrame, tf: str, grid4h: str = "forex") -> pd.DataFrame:
    """Phase-3 bare CISD book on `tf`: series_open, swing 2/2, max_wait 3,
    decide at the confirming bar's close, stop at the protected swing, 2R."""
    b = cl.build_bars(m1, tf, grid4h=grid4h)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if len(b) < 10:
        return pd.DataFrame(columns=cols)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close,
        "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "rr": 2.0,
    })
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def last_closed_idx(bars: pd.DataFrame, times) -> np.ndarray:
    """Row position of the last bar of `bars` with close_time <= t (-1 if none)."""
    ct = cl.data.utc_ns(pd.DatetimeIndex(bars["close_time"]))
    t = cl.data.utc_ns(pd.DatetimeIndex(times))
    return np.searchsorted(ct, t, side="right") - 1


def summary(res: dict) -> str:
    keys = ("n", "n_gated", "avg_R", "observed_rate", "null_rate", "diff", "ci_lo",
            "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars",
            "gate_rate", "ctrl_overlap", "halves", "dependence")
    return "\n".join(f"  {k:15s} {res[k]}" for k in keys if res.get(k) is not None)
