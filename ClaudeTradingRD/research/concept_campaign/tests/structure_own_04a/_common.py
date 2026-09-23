"""Shared, pure helpers for batch structure_own_04a (TTrades own-voice structure concepts).

Every function takes the M1 frame / bars it is handed (bars built with cl.build_bars
from the INPUT), so detectors built on it stay pure for concept_lab.probe_lookahead.
No module state.
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
PHASE3_SRC = ("phase3: meta/conjunction_preregistration.md §1.8-1.16 (locked rung-0 CISD: "
              "series_open, 2/2, max_wait 3, stop = protected swing, 2R, 10 entry-TF bars)")
GRID_SRC = "session_window_fit: forex 4H grid for gold (17/21/01/05/09/13 NY); carried as a knob per Conjunction Test"


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


class LiveCandle:
    """In-progress state of the HTF candle, from M1 bars only.

    For every M1 bar k: the HTF bucket it belongs to, that bucket's open (first M1
    open), and the running high / low of the bucket up to and including bar k.
    `at(times)` returns, for each time t, the state after the last M1 bar that has
    CLOSED by t (bar start + 1 min <= t): the candle containing minute t-1. At an
    HTF boundary this is the just-completed candle (fully formed, fully known).
    """

    def __init__(self, m1: pd.DataFrame, m: M1, tf: str, grid4h: str = "forex"):
        b = cl.build_bars(m1, tf, grid4h=grid4h)
        st = ns(b.index)
        ct = ns(b["close_time"])
        k = np.searchsorted(st, m.t, side="right") - 1
        ok = (k >= 0) & (m.t < ct[np.clip(k, 0, None)])
        k = np.where(ok, k, -1)
        self.bucket = k
        self.bstart = st
        self.bclose = ct
        first = np.r_[True, k[1:] != k[:-1]] if len(k) else np.zeros(0, bool)
        idx_first = np.where(first, np.arange(len(k)), 0)
        idx_first = np.maximum.accumulate(idx_first)
        self.open = m.o[idx_first]
        self.hi = pd.Series(m.h).groupby(k).cummax().to_numpy()
        self.lo = pd.Series(m.l).groupby(k).cummin().to_numpy()
        self.m = m

    def at(self, times_ns: np.ndarray) -> dict:
        m = self.m
        j = np.searchsorted(m.t + ONE_MIN, np.asarray(times_ns, np.int64), side="right") - 1
        ok = j >= 0
        jj = np.clip(j, 0, None)
        ok &= self.bucket[jj] >= 0
        # the M1 bar must be the one just before t (no stale state across a data hole)
        ok &= (np.asarray(times_ns, np.int64) - (m.t[jj] + ONE_MIN)) < 30 * ONE_MIN
        out = {
            "ok": ok,
            "price": np.where(ok, m.c[jj], np.nan),
            "open": np.where(ok, self.open[jj], np.nan),
            "hi": np.where(ok, self.hi[jj], np.nan),
            "lo": np.where(ok, self.lo[jj], np.nan),
            "bucket": np.where(ok, self.bucket[jj], -1),
        }
        return out


def live_support(st: dict, d: np.ndarray, rule: str) -> np.ndarray:
    """Does the in-progress candle support expansion in direction d?

    'green': price is beyond the candle's open in direction d.
    'wick' : green AND opposing run (open -> extreme against d) <= |price - open|
             (small wick / large body, threshold_fits grade-A crossover 1.0).
    """
    o, p, hi, lo = st["open"], st["price"], st["hi"], st["lo"]
    body = d * (p - o)
    green = st["ok"] & (body > 0)
    if rule == "green":
        return green
    opp = np.where(d > 0, o - lo, hi - o)
    return green & (opp <= body)


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


def first_touch(m: M1, start_ns: int, end_ns: int, level: float, bullish: bool) -> int:
    """First M1 bar starting in [start_ns, end_ns) reaching `level` from above
    (bullish: low <= level) or below (bearish: high >= level). -1 if none."""
    i0 = int(np.searchsorted(m.t, start_ns, side="left"))
    i1 = int(np.searchsorted(m.t, end_ns, side="left"))
    if i1 <= i0:
        return -1
    seg = (m.l[i0:i1] <= level) if bullish else (m.h[i0:i1] >= level)
    k = np.flatnonzero(seg)
    return i0 + int(k[0]) if len(k) else -1
