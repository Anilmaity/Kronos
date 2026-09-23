"""Shared pure helpers for batch structure_own_05b (no lookahead: every helper is a
function of the bars it is given)."""
from __future__ import annotations

import numpy as np
import pandas as pd

ONE_MIN = pd.Timedelta(minutes=1)
PY = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python"


def m1_arrays(m1: pd.DataFrame):
    t = m1.index.values.astype("datetime64[ns]").astype(np.int64)
    return t, m1["high"].to_numpy(float), m1["low"].to_numpy(float)


def ns(ts) -> np.ndarray:
    return pd.DatetimeIndex(ts).tz_convert("UTC").as_unit("ns").asi8


def from_ns(a) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(np.asarray(a, dtype="int64").astype("datetime64[ns]")).tz_localize("UTC")


def swings22(h: np.ndarray, l: np.ndarray):
    """Fractal 2/2 swing highs/lows (strictly beyond the 2 bars before, >= the 2 after).
    A swing at i is confirmed at the CLOSE of bar i+2."""
    n = len(h)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    if n >= 5:
        c = slice(2, n - 2)
        sh[c] = (h[2:-2] > h[1:-3]) & (h[2:-2] > h[:-4]) & (h[2:-2] >= h[3:-1]) & (h[2:-2] >= h[4:])
        sl[c] = (l[2:-2] < l[1:-3]) & (l[2:-2] < l[:-4]) & (l[2:-2] <= l[3:-1]) & (l[2:-2] <= l[4:])
    return sh, sl


def show(res):
    for k in ("n", "avg_R", "win_rate", "observed_rate", "null_rate", "diff", "ci_lo",
              "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties",
              "ctrl_overlap", "complement", "gate_rate", "dependence"):
        if res.get(k) is not None:
            print(f"  {k:15s} {res[k]}")
