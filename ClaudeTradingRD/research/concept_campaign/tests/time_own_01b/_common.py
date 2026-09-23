"""Shared, pure helpers for batch time_own_01b (time, TTrades own voice).

Everything is a pure function of the M1 frame it is given (bars built with
cl.build_bars / lookups passed m1=...), so probe_lookahead can re-run it on
truncated slices.

Baseline trade book where a concept is a filter: the phase-3 locked rung-0 CISD
(meta/conjunction_preregistration.md §1.8-1.13): series_open level, 2/2 swings,
max_wait 3, min_series 1; decide at the confirming bar's close; enter next M1 open;
stop = protected swing; 2R; hold 10 entry-TF bars.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from concept_lab.data import utc_ns, TZ  # noqa: E402
from detectors.cisd import cisd_events   # noqa: E402

CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
PHASE3_SRC = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked rung-0 config)"
OHLC = ["open", "high", "low", "close"]


def cisd_book(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Phase-3 rung-0 CISD trade frame on `tf` bars built from m1."""
    b = cl.build_bars(m1, tf)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if len(b) < 10:
        return empty(cols)
    ev = cisd_events(b[OHLC], **CISD_KW)
    if ev.empty:
        return empty(cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close,
        "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "rr": 2.0,
    })
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


def empty(cols) -> pd.DataFrame:
    out = pd.DataFrame({c: pd.Series(dtype="float64") for c in cols})
    for c in ("decision_time", "available_at"):
        if c in out:
            out[c] = pd.Series(dtype="datetime64[ns, UTC]")
    return out


def ny_mod(times) -> np.ndarray:
    """NY minute-of-day (DST-aware)."""
    return cl.ny_minute_of_day(pd.DatetimeIndex(times))


def ny_dates(m1: pd.DataFrame) -> np.ndarray:
    """Distinct NY calendar dates (weekdays) present in m1."""
    loc = pd.DatetimeIndex(m1.index).tz_convert(TZ)
    d = np.unique(loc.normalize().tz_localize(None).to_numpy())
    d = pd.DatetimeIndex(d)
    return d[d.dayofweek < 5]


def at_ny(dates: pd.DatetimeIndex, hhmm: str) -> pd.DatetimeIndex:
    """UTC instants of NY wall-clock hh:mm on each (naive) NY date."""
    h, m = map(int, hhmm.split(":"))
    loc = pd.DatetimeIndex(dates) + pd.Timedelta(hours=h, minutes=m)
    return loc.tz_localize(TZ, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")


def bar_pos_exact(m1: pd.DataFrame, times) -> np.ndarray:
    """Position of the M1 bar starting exactly at each time, else -1."""
    tn = utc_ns(m1.index)
    q = utc_ns(pd.DatetimeIndex(times))
    p = np.searchsorted(tn, q, side="left")
    pc = np.minimum(p, len(tn) - 1)
    ok = (p < len(tn)) & (tn[pc] == q)
    return np.where(ok, pc, -1)
