"""Shared pieces for batch risk_own_02a (my own code; the harness is untouched).

Baseline book for every gate in this batch: the campaign's canonical rung-0 CISD
book on 15m (concept_lab README example 2 / phase-3 locked config): series_open
level, 2/2 swings, max_wait 3, min_series 1, stop at the protected swing, 2R
target, decide at the confirming bar's close, enter the next M1 open, hold 10 bars.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402,F401

TF = "15min"
HOLD = "150min"
BASE_PARAMS = {"baseline_tf": TF, "level_rule": "series_open", "swing": "2/2",
               "max_wait": 3, "min_series": 1, "rr": 2.0, "max_hold": HOLD, "grid4h": "n/a"}
BASE_SRC = {
    "baseline_tf": "phase3: primary stack entry TF (README gate example uses the 15m book)",
    "level_rule": "phase3: meta/conjunction_preregistration.md locked rung-0 config",
    "swing": "phase3: meta/conjunction_preregistration.md locked rung-0 config",
    "max_wait": "phase3: meta/conjunction_preregistration.md locked rung-0 config",
    "min_series": "phase3: meta/conjunction_preregistration.md locked rung-0 config",
    "rr": "phase3: locked 2R target (method_spec 2R floor)",
    "max_hold": "phase3: 10 entry-TF bars, as in the concept_lab README examples",
    "grid4h": "declared-before-run: no 4h bars are used",
}
BASE_RULE = ("baseline: 15m rung-0 CISD book (series_open level, 2/2 swings, max_wait 3, "
             "stop at protected swing, 2R, hold 150min, entry next M1 open)")
MIN_N_M1 = 600          # a 'real' trading day (stub sessions from data holes are skipped)
MIN_N_M1_SRC = "declared-before-run: skip data-hole stub days (README trap 6)"


def cisd_book(m1: pd.DataFrame, tf: str = TF):
    """(events, raw cisd rows, bars). events carries the harness columns plus
    helpers: ext_pos (bar position of the protected extreme), confirm_close."""
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return pd.DataFrame(columns=cols + ["ext_pos", "confirm_close"]), ev, b
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close,
        "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "rr": 2.0,
    })
    out["ext_pos"] = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    out["conf_pos"] = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    out["confirm_close"] = ev["confirm_close"].to_numpy(float)
    return out, ev, b


def real_days(m1: pd.DataFrame, min_n_m1: int = MIN_N_M1) -> pd.DataFrame:
    """Completed-able trading days (18:00 NY roll) with >= min_n_m1 M1 bars."""
    d = cl.build_bars(m1, "1D")
    return d[d["n_m1"] >= min_n_m1].copy()


def asof_rows(frame: pd.DataFrame, avail, times) -> pd.DataFrame:
    """Row of `frame` with the latest avail <= t (NaN row if none)."""
    an = cl.data.utc_ns(pd.DatetimeIndex(avail))
    tn = cl.data.utc_ns(pd.DatetimeIndex(times))
    pos = np.searchsorted(an, tn, side="right") - 1
    ok = pos >= 0
    r = frame.iloc[np.clip(pos, 0, None)].reset_index(drop=True).astype(float)
    r.loc[~ok, :] = np.nan
    return r


def show(res: dict) -> None:
    keys = ("test_type", "claim", "n", "n_gated", "n_complement", "avg_R", "observed_rate",
            "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
            "ctrl_overlap", "ties", "exposure_bars", "gate_rate", "halves", "dependence")
    for k in keys:
        if res.get(k) is not None:
            print(f"  {k:15s} {res[k]}")
