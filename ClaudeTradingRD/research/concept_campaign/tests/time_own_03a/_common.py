"""Shared, PURE helpers for batch time_own_03a (TTrades own-voice time concepts).

Every function builds its bars from the M1 frame it is handed (cl.build_bars), so a
detector that calls it can be re-run on truncated data by cl.probe_lookahead.

Conventions (declared before any run; each script cites them in params_source):
  * trading day rolls at 18:00 New York, DST-aware (session_window_fit, settled);
    cl.trading_day labels a session by the date it OPENED (Monday's session = Sunday).
  * MIN_DAY_M1 = 600: stub sessions (data holes, README trap 6) are dropped before a
    "previous day" is taken. Fixed count (not a median) so truncation cannot move it.
  * C2 closure, method spec §3.2: bullish low<prev low AND close>prev low; bearish
    high>prev high AND close<prev high; a candle that is both is two-sided.
  * CISD: detectors.cisd.cisd_events, level series_open, swing 2/2, max_wait 3,
    min_series 1 (phase3 locked config).
  * Session partition of the NY clock for "the session in which an extreme formed"
    (daily-wick-confirmation-timeframes): Asia [18:00, 02:00), London [02:00, 07:00),
    New York [07:00, 17:00). Boundaries = the killzone starts (London 02:00, forex
    NY AM 07:00, killzones.yaml via session_window_fit), day open 18:00.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                  # noqa: E402
from detectors.cisd import cisd_events                    # noqa: E402

OHLC = ["open", "high", "low", "close"]
TZ = "America/New_York"
MIN_DAY_M1 = 600
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)


def daily(m1: pd.DataFrame) -> pd.DataFrame:
    """18:00-NY daily bars, stub sessions removed, with prev-day columns, session
    date (sdate) and weekday (0=Mon) of the session."""
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_DAY_M1].copy()
    for c in OHLC:
        d["p_" + c] = d[c].shift(1)
    d["p_tday"] = pd.DatetimeIndex(d["trading_day"]).to_series(index=d.index).shift(1)
    sdate = pd.DatetimeIndex(d["trading_day"]) + pd.Timedelta(days=1)
    d["sdate"] = sdate
    d["wd"] = sdate.dayofweek
    gap = (pd.DatetimeIndex(d["trading_day"]) - pd.DatetimeIndex(d["p_tday"])).days
    d["p_ok"] = np.asarray((gap >= 1) & (gap <= 4))
    return d


def c2_flags(d: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    bull = ((d["low"] < d["p_low"]) & (d["close"] > d["p_low"])).fillna(False).to_numpy()
    bear = ((d["high"] > d["p_high"]) & (d["close"] < d["p_high"])).fillna(False).to_numpy()
    return bull, bear


def day_end_utc(tday) -> pd.DatetimeIndex:
    """17:00 NY at the end of trading day `tday` (naive date of the 18:00 open)."""
    loc = pd.DatetimeIndex(tday) + pd.Timedelta(days=1, hours=17)
    return loc.tz_localize(TZ).tz_convert("UTC")


def ny_session(times) -> np.ndarray:
    """'asia' [18:00,02:00), 'london' [02:00,07:00), 'ny' [07:00,17:00) NY clock."""
    m = cl.ny_minute_of_day(pd.DatetimeIndex(times))
    return np.where((m >= 120) & (m < 420), "london",
                    np.where((m >= 420) & (m < 1020), "ny", "asia"))


def running_extremes_at(m1: pd.DataFrame, times) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    """Trading-day running low/high over M1 bars that START before each time (i.e. all
    closed M1 bars up to that moment), and the trading day of that last bar."""
    td = cl.trading_day(m1.index)
    g = pd.Series(m1["low"].to_numpy(), index=m1.index).groupby(td.values)
    lo = g.cummin().to_numpy()
    hi = pd.Series(m1["high"].to_numpy(), index=m1.index).groupby(td.values).cummax().to_numpy()
    tn = m1.index.asi8
    q = pd.DatetimeIndex(times).tz_convert("UTC").as_unit("ns").asi8
    pos = np.searchsorted(tn, q, side="left") - 1
    ok = pos >= 0
    posc = np.clip(pos, 0, len(tn) - 1)
    rlo = np.where(ok, lo[posc], np.nan)
    rhi = np.where(ok, hi[posc], np.nan)
    rtd = pd.DatetimeIndex(np.asarray(td)[posc])
    return rlo, rhi, rtd


def cisd_frame(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    """CISD events on `tf` bars with decision (= confirming bar close) attached."""
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[OHLC], **CISD_KW)
    if ev.empty:
        return ev.assign(decision_time=pd.Series(dtype="datetime64[ns, UTC]"), tf=tf)
    ev = ev.copy()
    ev["decision_time"] = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"]).tz_convert("UTC")
    ev["tf"] = tf
    return ev


def trading_minutes(start_utc, end_utc) -> pd.Timedelta:
    """Wall-clock span minus the 17:00-18:00 NY daily halts and the weekend halt
    (pure clock arithmetic), for hold_basis='bars' holds that end at a clock time."""
    s = pd.Timestamp(start_utc).tz_convert(TZ)
    e = pd.Timestamp(end_utc).tz_convert(TZ)
    if e <= s:
        return pd.Timedelta(0)
    halts = pd.Timedelta(0)
    day = s.normalize()
    while day <= e.normalize():
        wd = day.dayofweek
        if wd == 4:
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
    return ((e - s) - halts).floor("min")


def show(res: dict) -> None:
    for k in ("test_type", "n", "n_gated", "n_complement", "avg_R", "observed_rate", "null_rate",
              "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars",
              "ties", "ctrl_overlap", "gate_rate", "dependence"):
        if res.get(k) is not None:
            print(f"  {k:14s} {res[k]}")
