"""Shared, pure helpers for batch structure_own_02b (TTrades own-voice structure concepts).

Every function takes the M1 frame / bars it is given (bars are built with
cl.build_bars from the INPUT), so detectors built on it stay pure for
concept_lab.probe_lookahead. No module state.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import concept_lab as cl      # noqa: E402
from detectors.cisd import cisd_events              # noqa: E402
from detectors.primitives import swing_points       # noqa: E402

OHLC = ["open", "high", "low", "close"]
ONE_MIN = np.int64(60_000_000_000)
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
PHASE3_SRC = "phase3: meta/conjunction_preregistration.md §1.8-1.16 (locked rung-0 CISD: series_open, 2/2, max_wait 3, stop = protected swing, 2R, 10 entry-TF bars)"


def ns(idx) -> np.ndarray:
    return pd.DatetimeIndex(idx).tz_convert("UTC").as_unit("ns").asi8


def to_ts(a) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(np.asarray(a, dtype="int64")).tz_localize("UTC")


def complete_bars(b: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    """Drop bars whose nominal close is after the last M1 minute of the slice."""
    if b.empty or m1.empty:
        return b
    end = pd.Timestamp(m1.index[-1]).tz_convert("UTC") + pd.Timedelta(minutes=1)
    return b[pd.DatetimeIndex(b["close_time"]).tz_convert("UTC") <= end]


def empty(cols) -> pd.DataFrame:
    out = pd.DataFrame({c: pd.Series(dtype="float64") for c in cols})
    for c in ("decision_time", "available_at"):
        if c in out:
            out[c] = pd.Series(dtype="datetime64[ns, UTC]")
    return out


def cisd_frame(b: pd.DataFrame, **kw) -> pd.DataFrame:
    """cisd_events on a bar frame plus positional indices, confirm bar close_time, sign."""
    ev = cisd_events(b[OHLC], **{**CISD_KW, **kw})
    if ev.empty:
        return ev.assign(conf_pos=pd.Series(dtype=int), ext_pos=pd.Series(dtype=int),
                         s_pos=pd.Series(dtype=int), e_pos=pd.Series(dtype=int),
                         conf_close_time=pd.Series(dtype="datetime64[ns, UTC]"),
                         sgn=pd.Series(dtype=int))
    idx = b.index
    ev = ev.copy()
    ev["conf_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    ev["ext_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    ev["s_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["series_start"]))
    ev["e_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["series_end"]))
    ev["conf_close_time"] = pd.DatetimeIndex(b["close_time"].to_numpy()[ev["conf_pos"].to_numpy()])
    ev["sgn"] = np.where(ev["direction"] == "bullish", 1, -1)
    return ev.reset_index(drop=True)


def bar_arrays(b: pd.DataFrame, left: int = 2, right: int = 2) -> dict:
    sw = swing_points(b[OHLC], left=left, right=right)
    return {
        "o": b["open"].to_numpy(float), "h": b["high"].to_numpy(float),
        "l": b["low"].to_numpy(float), "c": b["close"].to_numpy(float),
        "ct": ns(b["close_time"]), "st": ns(b.index),
        "sh": sw["swing_high"].to_numpy(bool), "sl": sw["swing_low"].to_numpy(bool),
    }


def fvg_arrays(h: np.ndarray, l: np.ndarray):
    """3-bar FVGs stamped on the third bar i (wick test). bull: low[i] > high[i-2]."""
    n = len(h)
    bull = np.zeros(n, bool)
    bear = np.zeros(n, bool)
    if n >= 3:
        bull[2:] = l[2:] > h[:-2]
        bear[2:] = h[2:] < l[:-2]
    glo = np.full(n, np.nan)
    ghi = np.full(n, np.nan)
    if n >= 3:
        glo[2:] = np.where(bull[2:], h[:-2], np.where(bear[2:], h[2:], np.nan))
        ghi[2:] = np.where(bull[2:], l[2:], np.where(bear[2:], l[:-2], np.nan))
    return bull, bear, glo, ghi


def atr(b: pd.DataFrame, n: int = 20) -> np.ndarray:
    """ATR(n) of CLOSED bars up to and including each bar (known at its close)."""
    h, l, c = b["high"].to_numpy(float), b["low"].to_numpy(float), b["close"].to_numpy(float)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


class M1:
    """Numpy views of the M1 slice a detector was handed."""

    def __init__(self, m1: pd.DataFrame):
        self.t = ns(m1.index)
        self.o = m1["open"].to_numpy(float)
        self.h = m1["high"].to_numpy(float)
        self.l = m1["low"].to_numpy(float)
        self.c = m1["close"].to_numpy(float)
        self.n = len(self.t)


def first_touch(m: M1, start_ns: int, end_ns: int, level: float, bullish: bool,
                cancel: float | None = None) -> int:
    """First M1 bar starting in [start_ns, end_ns) that reaches `level` (bullish: low <=
    level; bearish: high >= level), unless an earlier-or-same bar breached `cancel`
    (bullish: low < cancel; bearish: high > cancel) -> -1. Returns M1 position or -1."""
    i0 = int(np.searchsorted(m.t, start_ns, side="left"))
    i1 = int(np.searchsorted(m.t, end_ns, side="left"))
    if i1 <= i0:
        return -1
    if bullish:
        hit = m.l[i0:i1] <= level
        bad = (m.l[i0:i1] < cancel) if cancel is not None else np.zeros(i1 - i0, bool)
    else:
        hit = m.h[i0:i1] >= level
        bad = (m.h[i0:i1] > cancel) if cancel is not None else np.zeros(i1 - i0, bool)
    ev = hit | bad
    if not ev.any():
        return -1
    k = int(np.argmax(ev))
    if bad[k]:
        return -1
    return i0 + k
