"""Shared helpers for batch time_guest_01a (read-only use of concept_lab)."""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np  # noqa: E402,F401
import pandas as pd  # noqa: E402,F401

import concept_lab as cl  # noqa: E402,F401
from concept_lab.examples import detect_cisd  # noqa: E402,F401

PHASE3_CISD = ("phase3: meta/conjunction_preregistration.md §1.8-1.13 locked config "
               "(series_open level, 2/2 swings, max_wait 3, min_series 1, stop at protected "
               "swing, 2R, max hold 10 entry-TF periods)")


def show(res: dict) -> None:
    keys = ("n", "n_complement", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
            "verdict_detail", "observed_rate", "null_rate", "ties", "exposure_bars",
            "ctrl_overlap", "gate_rate", "firing_rate")
    for k in keys:
        if k in res:
            print(f"  {k}: {res[k]}")


def swings_confirmed(b: pd.DataFrame, left: int = 2, right: int = 2) -> pd.DataFrame:
    """Fractal swings with the CLOSE time of the confirming bar (not its start).
    (Copied from model_guest_01b/_common.py so both C2U books share one definition.)"""
    h, l = b["high"].to_numpy(), b["low"].to_numpy()
    n = len(b)
    ish = np.zeros(n, bool)
    isl = np.zeros(n, bool)
    for i in range(left, n - right):
        if (h[i - left:i] < h[i]).all() and (h[i + 1:i + 1 + right] <= h[i]).all():
            ish[i] = True
        if (l[i - left:i] > l[i]).all() and (l[i + 1:i + 1 + right] >= l[i]).all():
            isl[i] = True
    ct = pd.DatetimeIndex(b["close_time"])
    conf = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    idx = np.arange(n)
    ok = idx + right < n
    conf[ok] = ct.tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy()[idx[ok] + right]
    return pd.DataFrame({"sh": ish, "sl": isl, "high": h, "low": l,
                         "conf": pd.DatetimeIndex(conf).tz_localize("UTC")}, index=b.index)
