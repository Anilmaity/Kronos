"""Shared, pure building blocks for batch model_own_02a (TTrades own-voice models).

Every function takes bars built FROM THE DETECTOR'S INPUT M1 (cl.build_bars), so the
detectors that use them stay probe-able. Nothing here reads a bar before its close_time.

Definitions (all from meta/ttrades_method_spec.md unless noted):
  C2 closure (§3.2): bull  low[i] < low[i-1] and close[i] > low[i-1]
                     bear  high[i] > high[i-1] and close[i] < high[i-1]
  C3 closure, Reading A (§3.3): the candle after C2 closes beyond C2's OPEN.
  CISD (§4.2): detectors.cisd.cisd_events, level_rule='series_open' (the spec's default),
               2/2 swing, max_wait=3 (phase-3 locked config) -> protected swing = extreme.
  FVG (§3.9): bull low[i+1] > high[i-1]; bear high[i+1] < low[i-1]; known at bar i+1 close.
"""
from __future__ import annotations

import sys

PY = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python"
if PY not in sys.path:
    sys.path.insert(0, PY)

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

OHLC = ["open", "high", "low", "close"]


def utc(x) -> pd.DatetimeIndex:
    d = pd.DatetimeIndex(x)
    return d.tz_localize("UTC") if d.tz is None else d.tz_convert("UTC")


def cisd(b: pd.DataFrame, max_wait: int = 3) -> pd.DataFrame:
    """CISD events on bars `b`, stamped at the confirming bar's close."""
    cols = ["decision_time", "direction", "stop_px", "confirm_close", "confirm_start",
            "extreme_start", "extreme_close_time"]
    ev = cisd_events(b[OHLC], level_rule="series_open", left=2, right=2,
                     max_wait=max_wait, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame({
        "decision_time": utc(b.loc[ev["confirm_time"], "close_time"].to_numpy()),
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "confirm_close": ev["confirm_close"].to_numpy(float),
        "confirm_start": utc(ev["confirm_time"].to_numpy()),
        "extreme_start": utc(ev["extreme_time"].to_numpy()),
        "extreme_close_time": utc(b.loc[ev["extreme_time"], "close_time"].to_numpy()),
    })
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def c2_flags(b: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    lo, hi, c = b["low"].to_numpy(), b["high"].to_numpy(), b["close"].to_numpy()
    pl = np.r_[np.nan, lo[:-1]]
    ph = np.r_[np.nan, hi[:-1]]
    bull = (lo < pl) & (c > pl)
    bear = (hi > ph) & (c < ph)
    return bull, bear


def c3a_flags(b: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """C3 closure Reading A after a C2 at i-1: close[i] beyond open[i-1] in direction."""
    bull2, bear2 = c2_flags(b)
    o, c = b["open"].to_numpy(), b["close"].to_numpy()
    po = np.r_[np.nan, o[:-1]]
    pb2 = np.r_[False, bull2[:-1]]
    pr2 = np.r_[False, bear2[:-1]]
    return pb2 & (c > po), pr2 & (c < po)


def last_closed(bars_: pd.DataFrame, times) -> np.ndarray:
    """Position of the last bar with close_time <= t (-1 if none)."""
    ct = cl.data.utc_ns(utc(bars_["close_time"].to_numpy()))
    return np.searchsorted(ct, cl.data.utc_ns(utc(times)), side="right") - 1


def containing(bars_: pd.DataFrame, times) -> np.ndarray:
    """Position of the bar with start < t <= close_time (the bar in progress at t, or the
    bar that just closed exactly at t). -1 if none."""
    st = cl.data.utc_ns(utc(bars_.index))
    ct = cl.data.utc_ns(utc(bars_["close_time"].to_numpy()))
    tn = cl.data.utc_ns(utc(times))
    p = np.searchsorted(st, tn, side="left") - 1
    ok = (p >= 0)
    pc = np.clip(p, 0, None)
    ok &= tn <= ct[pc]
    return np.where(ok, p, -1)


def running_in_parent(child: pd.DataFrame, parent: pd.DataFrame) -> pd.DataFrame:
    """For every child bar: the parent bar containing it, the parent's open, and the
    parent's running high/low up to and including this child bar (known at the child's
    close). Children must nest inside parents (15m in 4H forex grid / 18:00 day: true)."""
    p = containing(parent, child.index + pd.Timedelta(seconds=1))
    key = pd.Series(p)
    hi = pd.Series(child["high"].to_numpy()).groupby(key).cummax().to_numpy()
    lo = pd.Series(child["low"].to_numpy()).groupby(key).cummin().to_numpy()
    first_open = pd.Series(child["open"].to_numpy()).groupby(key).transform("first").to_numpy()
    return pd.DataFrame({"parent": p, "p_open": first_open, "run_hi": hi, "run_lo": lo},
                        index=child.index)


def swings(b: pd.DataFrame, left: int = 2, right: int = 2):
    """2/2 fractal swing highs/lows with the time they become known (close of bar i+right)."""
    h, lo = b["high"].to_numpy(), b["low"].to_numpy()
    n = len(b)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    for i in range(left, n - right):
        if h[i] > h[i - left:i].max() and h[i] > h[i + 1:i + 1 + right].max():
            sh[i] = True
        if lo[i] < lo[i - left:i].min() and lo[i] < lo[i + 1:i + 1 + right].min():
            sl[i] = True
    ct = utc(b["close_time"].to_numpy())
    kn = cl.data.utc_ns(ct).astype("int64")
    known = np.r_[kn[right:], np.full(right, -1, dtype=np.int64)]
    return sh, sl, known          # known: ns int of confirmation time (-1 = not yet)


def fvgs(b: pd.DataFrame) -> pd.DataFrame:
    """Three-bar FVGs stamped when known (close of the third bar)."""
    h, lo = b["high"].to_numpy(), b["low"].to_numpy()
    ct = utc(b["close_time"].to_numpy())
    rows = []
    for i in range(1, len(b) - 1):
        if lo[i + 1] > h[i - 1]:
            rows.append((1, h[i - 1], lo[i + 1], i, ct[i + 1]))
        if h[i + 1] < lo[i - 1]:
            rows.append((-1, h[i + 1], lo[i - 1], i, ct[i + 1]))
    return pd.DataFrame(rows, columns=["direction", "bottom", "top", "mid_pos", "known_at"])


def ny_hm(times) -> np.ndarray:
    return cl.ny_minute_of_day(utc(times))


def in_progress(bars_: pd.DataFrame, times) -> np.ndarray:
    """Position of the bar with start <= t < close_time — the bar an entry taken at t
    trades inside. -1 if t falls in no bar (halt / gap)."""
    st = cl.data.utc_ns(utc(bars_.index))
    ct = cl.data.utc_ns(utc(bars_["close_time"].to_numpy()))
    tn = cl.data.utc_ns(utc(times))
    p = np.searchsorted(st, tn, side="right") - 1
    pc = np.clip(p, 0, None)
    ok = (p >= 0) & (tn < ct[pc])
    return np.where(ok, p, -1)
