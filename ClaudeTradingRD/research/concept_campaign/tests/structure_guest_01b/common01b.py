"""Shared primitives for batch structure_guest_01b (guest voice: AP, DexterLab, Alex's Options).

Every function is pure: bars built from the M1 slice handed in, and every decision uses
only bars whose close is <= the decision time.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

NS_MIN = np.int64(60 * 10 ** 9)


def bars_arr(b: pd.DataFrame) -> dict:
    return {"start": cl.data.utc_ns(b.index).view("int64"),
            "close_t": cl.data.utc_ns(b["close_time"]).view("int64"),
            "o": b["open"].to_numpy(float), "h": b["high"].to_numpy(float),
            "l": b["low"].to_numpy(float), "c": b["close"].to_numpy(float)}


def to_utc(ns) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(np.asarray(ns, "int64").astype("datetime64[ns]")).tz_localize("UTC")


def swing_flags(h: np.ndarray, l: np.ndarray, left: int = 2, right: int = 2):
    """Fractal swings: high[j] > the `left` highs before and >= the `right` after.
    Known at the close of bar j+right."""
    n = len(h)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    if n < left + right + 1:
        return sh, sl
    core = slice(left, n - right)
    okh = np.ones(n - left - right, bool)
    okl = np.ones(n - left - right, bool)
    hc, lc = h[core], l[core]
    for k in range(1, left + 1):
        okh &= hc > h[left - k:n - right - k]
        okl &= lc < l[left - k:n - right - k]
    for k in range(1, right + 1):
        okh &= hc >= h[left + k:n - right + k]
        okl &= lc <= l[left + k:n - right + k]
    sh[core] = okh
    sl[core] = okl
    return sh, sl


def structure_breaks(b: dict, left: int = 2, right: int = 2) -> pd.DataFrame:
    """Every CLOSE beyond the most recent confirmed, still-unbroken fractal swing.

    count = 1 for a flip (break against the previous break's direction), 2 for the
    next same-direction break after it (the 'second continuation'), 3, ... .
    The very first break of the slice has count 0 (no prior state; never scored).
    anchor = strong extreme: the lowest low (bull) / highest high (bear) between the
    broken swing bar and the breaking bar, inclusive.
    flip_bar = bar index of the flip that opened the current run (cluster id).
    """
    h, l, c = b["h"], b["l"], b["c"]
    n = len(h)
    sh, sl = swing_flags(h, l, left, right)
    act_h = act_l = -1
    state = 0
    count = 0
    flip_bar = -1
    rows = []
    for i in range(n):
        if act_h >= 0 and c[i] > h[act_h]:
            if state == 1:
                count = count + 1 if count > 0 else 0
            else:
                count = 1 if state == -1 else 0
                flip_bar = i
            seg = l[act_h:i + 1]
            rows.append((i, 1, count, float(seg.min()), float(h[act_h]), flip_bar))
            state = 1
            act_h = -1
        elif act_l >= 0 and c[i] < l[act_l]:
            if state == -1:
                count = count + 1 if count > 0 else 0
            else:
                count = 1 if state == 1 else 0
                flip_bar = i
            seg = h[act_l:i + 1]
            rows.append((i, -1, count, float(seg.max()), float(l[act_l]), flip_bar))
            state = -1
            act_l = -1
        j = i - right
        if j >= left:
            if sh[j]:
                act_h = j
            if sl[j]:
                act_l = j
    out = pd.DataFrame(rows, columns=["bar", "dir", "count", "anchor", "broken", "flip_bar"])
    out["t"] = b["close_t"][out["bar"].to_numpy()] if len(out) else np.array([], "int64")
    out["flip_t"] = b["close_t"][out["flip_bar"].to_numpy()] if len(out) else np.array([], "int64")
    return out


def strat_types(h: np.ndarray, l: np.ndarray) -> np.ndarray:
    """TheSTRAT type per bar vs the previous bar: 0 = none (first bar), 1 inside,
    2 = 2-up, -2 = 2-down, 3 outside. Equal high/low does NOT count as taken."""
    n = len(h)
    t = np.zeros(n, int)
    if n < 2:
        return t
    up = h[1:] > h[:-1]
    dn = l[1:] < l[:-1]
    tt = np.where(up & dn, 3, np.where(up, 2, np.where(dn, -2, 1)))
    t[1:] = tt
    return t
