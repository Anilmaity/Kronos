"""New York clock helpers and availability-stamped levels.

Everything returned here that is a *level* (a high, a low, an open) carries the
UTC moment it became knowable (`available_at`), and the lookups (`prior_hilo`,
`open_at`, `running_hilo`) only ever return levels with `available_at <= t`. Use
these instead of hand-rolled groupbys — a hand-rolled "prior day high" that is
joined by calendar date is the classic way to read today's high at 09:00.

Windows are [start, end) on the NY wall clock with DST; a window whose end is <=
its start wraps midnight (Asia 20:00-00:00). Windows may not straddle the daily
roll (`day_open_hour`, 18:00 by default).

Provenance of the windows:
  * SESSION_WINDOWS — `detectors.bias.SESSION_WINDOWS` (method spec §2.5; Asia
    from killzones.yaml): asia 20:00-00:00, london 02:00-05:00, ny_am 08:30-12:00.
  * KILLZONES — `concepts/time/killzones.yaml`, verbatim-verified (phase 2):
    forex Asia 20-00, London 02-05, NY AM 07-10, London Close 10-12; indices NY AM
    08:30-11:00, NY PM 13:30-16:00. Taught convention, not a narrated gate.
  Settled caution (vault, *Session Timing on Gold*): there is no 18:00 kill zone —
  the reopen hour is a gap artefact; 08:30 is the densest half-hour for daily
  extremes AND sits inside the worst-expectancy hour.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from detectors.bias import SESSION_WINDOWS as _BIAS_WINDOWS
from .data import (utc_ns, TZ, load_m1, bars, asof, trading_day, normalize_tf, _localize,
                   DEFAULT_GRID_4H, DEFAULT_DAY_OPEN_HOUR, is_certified)

SESSION_WINDOWS = dict(_BIAS_WINDOWS)
KILLZONES = {
    "fx_asia": ("20:00", "00:00"),
    "fx_london": ("02:00", "05:00"),
    "fx_ny_am": ("07:00", "10:00"),
    "fx_london_close": ("10:00", "12:00"),
    "ix_asia": ("20:00", "00:00"),
    "ix_london": ("02:00", "05:00"),
    "ix_ny_am": ("08:30", "11:00"),
    "ix_ny_pm": ("13:30", "16:00"),
}

_MEMO: dict = {}


def _memo_get(key, m1):
    hit = _MEMO.get(key)
    if hit is None or hit[0] is not m1:              # id() can be reused after GC
        return None
    return hit[1]


def _memo_put(key, m1, val):
    _MEMO[key] = (m1, val)
    return val


def _win(window) -> tuple[str, str, str]:
    if isinstance(window, str):
        if window in SESSION_WINDOWS:
            a, b = SESSION_WINDOWS[window]
        elif window in KILLZONES:
            a, b = KILLZONES[window]
        else:
            raise KeyError(f"unknown window {window!r}; use a name from SESSION_WINDOWS/"
                           f"KILLZONES or a ('HH:MM','HH:MM') tuple")
        return a, b, window
    a, b = window
    return a, b, f"{a}-{b}"


def _hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def to_ny(times) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(times).tz_convert(TZ)


def ny_minute_of_day(times) -> np.ndarray:
    loc = to_ny(times)
    return (loc.hour * 60 + loc.minute).to_numpy()


def in_window(times, start: str, end: str) -> np.ndarray:
    """Boolean: NY wall-clock minute of `times` in [start, end) (wraps if end<=start)."""
    t = ny_minute_of_day(times)
    a, b = _hm(start), _hm(end)
    return (t >= a) & (t < b) if a < b else (t >= a) | (t < b)


def _m1(m1):
    return load_m1() if m1 is None else m1


def window_hilo(window, m1: pd.DataFrame | None = None,
                day_open_hour: int = DEFAULT_DAY_OPEN_HOUR) -> pd.DataFrame:
    """Per trading day: open/high/low/close of the M1 bars inside `window`.

    Indexed by trading day; `available_at` = the window's NOMINAL end in UTC
    (never earlier than its last minute + 1). `first_m1` = first traded minute.
    """
    a, b, name = _win(window)
    roll = day_open_hour * 60
    am, bm = _hm(a), _hm(b)
    straddles = (am < roll < bm) if am < bm else (roll > am or roll < bm)
    if straddles:
        raise ValueError(f"window {a}-{b} straddles the {day_open_hour}:00 daily roll")
    key = ("win", id(m1) if m1 is not None else "cert", a, b, day_open_hour)
    got = _memo_get(key, m1)
    if got is not None:
        return got.copy(deep=False)          # callers never share the memoised frame
    m = _m1(m1)
    idx = m.index
    mask = in_window(idx, a, b)
    sub = m[mask]
    t = sub.index
    loc = t.tz_convert(TZ).tz_localize(None)
    end_local = loc.normalize() + pd.Timedelta(minutes=bm)
    if bm <= am:                       # wraps midnight: bars at/after start end next day
        after = (loc.hour * 60 + loc.minute) >= am
        end_local = end_local + pd.to_timedelta(np.where(after, 1, 0), unit="D")
    td = trading_day(t, day_open_hour)
    df = pd.DataFrame({"open": sub["open"].to_numpy(), "high": sub["high"].to_numpy(),
                       "low": sub["low"].to_numpy(), "close": sub["close"].to_numpy(),
                       "_t": t, "_end": end_local}, index=td)
    g = df.groupby(level=0, sort=True)
    out = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                close=("close", "last"), n_m1=("open", "size"),
                first_m1=("_t", "min"), last_m1=("_t", "max"), _end=("_end", "first"))
    lm = pd.DatetimeIndex(out["last_m1"]) + pd.Timedelta(minutes=1)
    av = _localize(out["_end"].to_numpy(), lm)
    av = av.where(av >= lm, lm)
    out["available_at"] = av
    out = out.drop(columns="_end")
    out.index.name = "trading_day"
    out.attrs["window"] = f"{name} {a}-{b} NY"
    return _memo_put(key, m1, out).copy(deep=False)


def _source(kind, m1, grid4h, day_open_hour) -> pd.DataFrame:
    if isinstance(kind, tuple) or (isinstance(kind, str) and
                                   (kind in SESSION_WINDOWS or kind in KILLZONES)):
        w = window_hilo(kind, m1, day_open_hour)
        return w.assign(period_start=w["first_m1"])
    tf = normalize_tf(kind)
    b = bars(tf, grid4h, day_open_hour, None if is_certified(m1) else m1)
    return b.assign(available_at=b["close_time"], period_start=b.index)


def prior_hilo(times, kind="1D", n_back: int = 1, m1: pd.DataFrame | None = None,
               grid4h: str = DEFAULT_GRID_4H,
               day_open_hour: int = DEFAULT_DAY_OPEN_HOUR,
               min_coverage: float | None = None) -> pd.DataFrame:
    """The n-th most recent COMPLETED period's levels at each time t.

    kind: a timeframe ('1D' -> PDH/PDL, '1W' -> PWH/PWL, '1M', '4h', '1h', ...)
          or a window name / ('HH:MM','HH:MM') tuple (-> last completed session).
    Returns high, low, open, close, period_start, available_at (<= t always),
    n_m1 (M1 bars in that period) and coverage (n_m1 / the median n_m1 of that
    kind). NaT times give NaN rows.
    min_coverage: skip periods whose coverage is below this (e.g. 0.5 drops the
    stub "days" of a few dozen minutes that data holes create), so the level comes
    from the last period with real coverage. Default None keeps every period —
    check `coverage` and record the choice in operationalization.params.
    """
    src = _source(kind, m1, grid4h, day_open_hour)
    n_m1 = src["n_m1"].to_numpy(float)
    med = float(np.median(n_m1)) if len(n_m1) else np.nan
    src = src.assign(coverage=n_m1 / med if med > 0 else np.nan)
    if min_coverage is not None:
        src = src[src["coverage"].to_numpy() >= float(min_coverage)]
    av = pd.DatetimeIndex(src["available_at"]).tz_convert("UTC")
    order = np.argsort(utc_ns(av), kind="stable")
    src, av = src.iloc[order], av[order]
    tt = pd.DatetimeIndex(times).tz_convert("UTC")
    tn = utc_ns(tt)
    pos = np.searchsorted(utc_ns(av), tn, side="right") - n_back
    ok = (pos >= 0) & ~np.isnat(tn)          # NaT sorts last: it must never read a row
    cols = ["open", "high", "low", "close", "period_start", "available_at", "n_m1",
            "coverage"]
    out = src.iloc[np.clip(pos, 0, None)][cols].copy()
    out.index = tt
    if (~ok).any():
        out.loc[~ok, :] = np.nan
    return out


def open_at(times, hhmm: str = "00:00", m1: pd.DataFrame | None = None,
            day_open_hour: int = DEFAULT_DAY_OPEN_HOUR, max_delay_min: int = 5,
            same_trading_day: bool = True) -> pd.DataFrame:
    """The open price at NY `hhmm` (midnight open, 08:30 open, 18:00 day open…).

    Per trading day: the open of the first M1 bar in [hhmm, hhmm+max_delay).
    For each t returns (price, time) of the latest such open with time <= t;
    with `same_trading_day` it must belong to t's trading day, else NaN.
    """
    key = ("open", id(m1) if m1 is not None else "cert", hhmm, day_open_hour, max_delay_min)
    src = _memo_get(key, m1)
    if src is None:
        m = _m1(m1)
        a = _hm(hhmm)
        mod = ny_minute_of_day(m.index)
        sel = (mod >= a) & (mod < a + max_delay_min)
        sub = m[sel]
        td = trading_day(sub.index, day_open_hour)
        df = pd.DataFrame({"price": sub["open"].to_numpy(), "time": sub.index,
                           "trading_day": td})
        df = df.groupby("trading_day", sort=True).first().reset_index()
        src = _memo_put(key, m1, df.sort_values("time").reset_index(drop=True))
    tt = pd.DatetimeIndex(times).tz_convert("UTC")
    st = pd.DatetimeIndex(src["time"])
    pos = np.searchsorted(utc_ns(st), utc_ns(tt), side="right") - 1
    ok = pos >= 0
    p = np.clip(pos, 0, None)
    out = pd.DataFrame({"price": src["price"].to_numpy()[p],
                        "time": st[p], "trading_day": src["trading_day"].to_numpy()[p]},
                       index=tt)
    if same_trading_day:
        ok = ok & np.asarray(pd.DatetimeIndex(out["trading_day"]) ==
                             trading_day(tt, day_open_hour))
    out.loc[~ok, ["price"]] = np.nan
    out.loc[~ok, ["time"]] = pd.NaT
    return out


def running_hilo(times, period: str = "1D", m1: pd.DataFrame | None = None,
                 day_open_hour: int = DEFAULT_DAY_OPEN_HOUR) -> pd.DataFrame:
    """High/low of the CURRENT period so far, from M1 bars closed by t.

    period '1D' (trading day) or '1W'. NaN when no bar of t's period has closed yet.
    """
    p = normalize_tf(period)
    if p not in ("1D", "1W"):
        raise ValueError("running_hilo supports '1D' and '1W'")
    key = ("run", id(m1) if m1 is not None else "cert", p, day_open_hour)
    m = _m1(m1)
    got = _memo_get(key, m1)
    if got is None:
        td = trading_day(m.index, day_open_hour)
        if p == "1W":
            sd = td + (pd.Timedelta(days=1) if day_open_hour >= 12 else pd.Timedelta(0))
            td = sd - pd.to_timedelta(sd.dayofweek, unit="D")
        k = pd.Series(td.to_numpy())
        hi = pd.Series(m["high"].to_numpy()).groupby(k).cummax().to_numpy()
        lo = pd.Series(m["low"].to_numpy()).groupby(k).cummin().to_numpy()
        got = _memo_put(key, m1, (td.to_numpy(), hi, lo,
                                  utc_ns(m.index + pd.Timedelta(minutes=1))))
    kk, hi, lo, closes = got
    tt = pd.DatetimeIndex(times).tz_convert("UTC")
    pos = np.searchsorted(closes, utc_ns(tt), side="right") - 1
    ok = pos >= 0
    p_ = np.clip(pos, 0, None)
    tk = trading_day(tt, day_open_hour)
    if p == "1W":
        sd = tk + (pd.Timedelta(days=1) if day_open_hour >= 12 else pd.Timedelta(0))
        tk = sd - pd.to_timedelta(sd.dayofweek, unit="D")
    ok = ok & (kk[p_] == tk.to_numpy())
    return pd.DataFrame({"high": np.where(ok, hi[p_], np.nan),
                         "low": np.where(ok, lo[p_], np.nan)}, index=tt)
