"""Shared helpers for batch entry_own_02b (pure functions; no harness edits).

Everything here takes the M1 frame / bars it is given, so detectors built on it
stay pure for concept_lab.probe_lookahead.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                       # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

ONE_MIN = np.int64(60_000_000_000)


def ns(idx) -> np.ndarray:
    return pd.DatetimeIndex(idx).tz_convert("UTC").as_unit("ns").asi8


def to_ts(a) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(np.asarray(a, dtype="int64")).tz_localize("UTC")


class M1:
    """Numpy views of the M1 slice a detector was handed."""

    def __init__(self, m1: pd.DataFrame):
        self.t = ns(m1.index)
        self.o = m1["open"].to_numpy(float)
        self.h = m1["high"].to_numpy(float)
        self.l = m1["low"].to_numpy(float)
        self.c = m1["close"].to_numpy(float)
        self.n = len(self.t)

    def pos(self, t_ns) -> np.ndarray:
        """First M1 bar starting at or after t."""
        return np.searchsorted(self.t, t_ns, side="left")


def first_touch(m: M1, start_ns: int, end_ns: int, level: float, bullish: bool,
                cancel: float | None = None):
    """First M1 bar starting in [start_ns, end_ns) whose excursion reaches `level`
    (bullish: low <= level; bearish: high >= level), provided no EARLIER-or-same bar
    breached `cancel` (bullish: high > cancel; bearish: low < cancel).
    A bar that both touches and breaches `cancel` counts as a cancel (conservative).
    Returns the M1 position or -1."""
    i0 = int(np.searchsorted(m.t, start_ns, side="left"))
    i1 = int(np.searchsorted(m.t, end_ns, side="left"))
    if i1 <= i0:
        return -1
    if bullish:
        hit = m.l[i0:i1] <= level
        bad = (m.h[i0:i1] > cancel) if cancel is not None else np.zeros(i1 - i0, bool)
    else:
        hit = m.h[i0:i1] >= level
        bad = (m.l[i0:i1] < cancel) if cancel is not None else np.zeros(i1 - i0, bool)
    ev = hit | bad
    if not ev.any():
        return -1
    k = int(np.argmax(ev))
    if bad[k]:
        return -1
    return i0 + k


def bars_with_swings(m1: pd.DataFrame, tf: str, left: int = 2, right: int = 2):
    """Bars built from the given M1 plus fractal swings. Returns (b, arrays dict)."""
    b = cl.build_bars(m1, tf)
    sw = swing_points(b[["open", "high", "low", "close"]], left=left, right=right)
    d = {
        "o": b["open"].to_numpy(float), "h": b["high"].to_numpy(float),
        "l": b["low"].to_numpy(float), "c": b["close"].to_numpy(float),
        "ct": ns(b["close_time"]), "st": ns(b.index),
        "sh": sw["swing_high"].to_numpy(bool), "sl": sw["swing_low"].to_numpy(bool),
    }
    return b, d


def fvg_arrays(d: dict):
    """3-bar FVGs stamped on the third bar i. bull: low[i] > high[i-2]."""
    h, l = d["h"], d["l"]
    n = len(h)
    bull = np.zeros(n, bool)
    bear = np.zeros(n, bool)
    if n >= 3:
        bull[2:] = l[2:] > h[:-2]
        bear[2:] = h[2:] < l[:-2]
    glo = np.full(n, np.nan)
    ghi = np.full(n, np.nan)
    glo[2:] = np.where(bull[2:], h[:-2], np.where(bear[2:], h[2:], np.nan))
    ghi[2:] = np.where(bull[2:], l[2:], np.where(bear[2:], l[:-2], np.nan))
    return bull, bear, glo, ghi


def empty(cols) -> pd.DataFrame:
    out = pd.DataFrame({c: pd.Series(dtype="float64") for c in cols})
    for c in ("decision_time", "available_at"):
        if c in out:
            out[c] = pd.Series(dtype="datetime64[ns, UTC]")
    return out


def displacement_legs(d: dict, right: int = 2) -> pd.DataFrame:
    """Structure-break displacement legs (both directions).

    Bullish: the last CONFIRMED swing high (fractal, known at bar pos+right close)
    is CLOSED above at bar k (the grade-A structural displacement gate). Leg low L =
    lowest low from that swing high to k. Leg high H = the first swing high at p >= k,
    known at bar p+right's close (= `arm_i`), with no low below L in [k, p+right].
    Mirror for bearish. One leg per (direction, p). Columns: dir, a_i (anchor bar),
    k_i, p_i, arm_i, L (anchor, 1.0), H (extreme, 0.0).
    """
    h, l, c = d["h"], d["l"], d["c"]
    sh, sl = d["sh"], d["sl"]
    n = len(h)
    rows = []
    for bull in (True, False):
        piv = sh if bull else sl          # the swing whose break is the displacement
        ext = sh if bull else sl          # the swing that ends the leg
        cur = -1
        broken = True
        seen = set()
        for j in range(n):
            if cur >= 0 and not broken:
                lvl = h[cur] if bull else l[cur]
                if (c[j] > lvl) if bull else (c[j] < lvl):
                    broken = True
                    k = j
                    seg = l[cur:k + 1] if bull else h[cur:k + 1]
                    a = cur + int(np.argmin(seg) if bull else np.argmax(seg))
                    anchor = l[a] if bull else h[a]
                    # first extreme swing at p >= k, confirmed at p+right < n
                    p = k
                    while p + right < n and not ext[p]:
                        p += 1
                    if p + right < n and ext[p] and p not in seen:
                        arm = p + right
                        intact = (l[k:arm + 1].min() >= anchor) if bull \
                            else (h[k:arm + 1].max() <= anchor)
                        if intact:
                            seen.add(p)
                            rows.append((1 if bull else -1, a, k, p, arm, anchor,
                                         h[p] if bull else l[p]))
            q = j - right
            if q >= 0 and piv[q]:
                cur, broken = q, False
    cols = ["dir", "a_i", "k_i", "p_i", "arm_i", "L", "H"]
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values(["arm_i", "dir"]).reset_index(drop=True)
