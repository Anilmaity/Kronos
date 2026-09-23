"""Shared, pure helpers for batch model_own_03a (weekly-profile family + session windows).

Everything here is a pure function of the M1 frame it is handed (built with
cl.build_bars), so a detector that calls it can be re-run on truncated data by
cl.probe_lookahead.

Conventions (all declared in each script's params_source):
  * trading day rolls at 18:00 New York (DST-aware); a day is labelled by its
    SESSION DATE (the Sunday-18:00 session is Monday);
  * stub days (n_m1 < 0.5 x the median day) are dropped before "previous day"
    is taken (README trap 6);
  * C2 closure, method spec §3.2: bullish low<prev low AND close>prev low;
    bearish high>prev high AND close<prev high;
  * hourly CISD inside a daily candle, method spec §2.4 step 3, via
    detectors.bias.hourly_cisd_in_candle (scope "range", level "series_open").
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                     # noqa: E402
from detectors.bias import hourly_cisd_in_candle             # noqa: E402

TZ = "America/New_York"
MIN_COVERAGE = 0.5


def daily_frame(m1: pd.DataFrame) -> pd.DataFrame:
    """1D bars (18:00 NY roll), stubs dropped, with weekday/week and prev-day columns."""
    d = cl.build_bars(m1, "1D")
    if d.empty:
        return d
    med = float(np.median(d["n_m1"].to_numpy(float)))
    d = d[d["n_m1"].to_numpy(float) >= MIN_COVERAGE * med].copy()
    sdate = pd.DatetimeIndex(d["trading_day"]) + pd.Timedelta(days=1)
    d["sdate"] = sdate
    d["wd"] = sdate.dayofweek                       # 0 = Monday ... 4 = Friday
    d["week"] = sdate - pd.to_timedelta(sdate.dayofweek, unit="D")
    for c in ("open", "high", "low", "close"):
        d["p_" + c] = d[c].shift(1)
    d["p_week"] = d["week"].shift(1)
    d["p_wd"] = d["wd"].shift(1)
    d = d[d["wd"] <= 4]                             # no weekend sessions on this venue
    return d


def c2_flags(d: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    bull = ((d["low"] < d["p_low"]) & (d["close"] > d["p_low"])).fillna(False).to_numpy()
    bear = ((d["high"] > d["p_high"]) & (d["close"] < d["p_high"])).fillna(False).to_numpy()
    return bull, bear


def cont_flags(d: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Continuation closure, method spec §2.3: close beyond the previous candle's extreme."""
    up = (d["close"] > d["p_high"]).fillna(False).to_numpy()
    dn = (d["close"] < d["p_low"]).fillna(False).to_numpy()
    return up, dn


def h1_cisd(h1: pd.DataFrame, day_label, day_close, direction: str) -> dict | None:
    """Hourly CISD inside one daily candle (bars whose START is in [label, close))."""
    end = pd.Timestamp(day_close) - pd.Timedelta(hours=1)
    ev = hourly_cisd_in_candle(h1[["open", "high", "low", "close"]], day_label, end,
                               direction, scope="range", level_rule="series_open")
    return ev


def friday_close_utc(week_monday) -> pd.Timestamp:
    """Friday 17:00 New York of the week whose Monday session date is given."""
    fri = pd.Timestamp(week_monday) + pd.Timedelta(days=4, hours=17)
    return fri.tz_localize(TZ).tz_convert("UTC")


def trading_minutes(start_utc, end_utc) -> pd.Timedelta:
    """Wall-clock minutes from start to end minus the 60-minute 17:00-18:00 NY halts
    crossed and the weekend halt. Pure clock arithmetic (no data), so a hold expressed
    this way with hold_basis='bars' ends at `end` for the real trade and gives the
    matched controls the same TRADABLE exposure."""
    s = pd.Timestamp(start_utc).tz_convert(TZ)
    e = pd.Timestamp(end_utc).tz_convert(TZ)
    if e <= s:
        return pd.Timedelta(0)
    total = (e - s)
    halts = pd.Timedelta(0)
    day = s.normalize()
    while day <= e.normalize():
        wd = day.dayofweek
        if wd == 4:                                         # Fri 17:00 -> Sun 18:00
            h0, h1 = day + pd.Timedelta(hours=17), day + pd.Timedelta(days=2, hours=18)
        elif wd in (0, 1, 2, 3):
            h0, h1 = day + pd.Timedelta(hours=17), day + pd.Timedelta(hours=18)
        else:
            day += pd.Timedelta(days=1)
            continue
        lo, hi = max(h0, s), min(h1, e)
        if hi > lo:
            halts += hi - lo
        day += pd.Timedelta(days=1)
    return (total - halts).floor("min")
