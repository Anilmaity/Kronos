"""Shared, PURE building blocks for batch model_own_01a (TTrades own-voice model concepts).

Every function takes the M1 frame it is given and builds its bars from it with
cl.build_bars, so probe_lookahead can re-run it on truncated slices. Nothing here
reads the in-progress higher-timeframe bar: a daily/4H/1H candle is only used once
its nominal close_time has passed, and intraday running extremes use closed 1h bars.

Parameters declared here (before any run) and their sources:
  MIN_DAY_M1 = 600       stub-session filter for a bias-source day (README trap 6:
                         data holes leave stub sessions such as 2025-12-08 = 56 M1).
                         Same cut as concept_lab.examples.example_rate.
  MIN_RISK_FRAC = 0.10   intraday books: stop distance must be >= 10% of the prior
                         day's range, so a stop sitting a few cents under a 1h low
                         that just printed is not scored as a setup.  declared.
  SWING 2/2 fractal      primitives.swing_points / phase3 locked swing fractal.
  CISD series_open, max_wait=3, min_series=1   phase3 locked CISD config (§1.16).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.bias import (daily_closures, hourly_cisd_in_candle,  # noqa: E402
                            previous_candle_state)
from detectors.cisd import cisd_events          # noqa: E402
from detectors.fractal import c2_events         # noqa: E402
from detectors.primitives import swing_points   # noqa: E402

OHLC = ["open", "high", "low", "close"]
MIN_DAY_M1 = 600
MIN_RISK_FRAC = 0.10
NY = "America/New_York"


def daily(m1: pd.DataFrame) -> pd.DataFrame:
    """Completed-or-not 18:00-NY daily bars, stub sessions removed."""
    d = cl.build_bars(m1, "1D")
    return d[d["n_m1"] >= MIN_DAY_M1].copy()


def _slice_idx(ltf_index_ns: np.ndarray, start, close) -> tuple[int, int]:
    a = int(np.searchsorted(ltf_index_ns, pd.Timestamp(start).value, side="left"))
    b = int(np.searchsorted(ltf_index_ns, pd.Timestamp(close).value, side="left"))
    return a, b


def ltf_cisd_inside(htf: pd.DataFrame, ltf: pd.DataFrame, rows: pd.DataFrame,
                    direction_col: str = "direction", scope: str = "range") -> np.ndarray:
    """For each row (an HTF candle, indexed by its start, with close_time), is there a
    LTF CISD in `direction` inside that candle (detectors.bias.hourly_cisd_in_candle,
    series_open level)? Only LTF bars starting before the HTF close are passed, so the
    verdict is known at the HTF close."""
    lt_ns = ltf.index.asi8 if ltf.index.tz is not None else ltf.index.asi8
    lt = ltf[OHLC]
    out = np.zeros(len(rows), dtype=bool)
    for k, (t, r) in enumerate(rows.iterrows()):
        a, b = _slice_idx(lt_ns, t, r["close_time"])
        if b - a < 3:
            continue
        seg = lt.iloc[a:b]
        ev = hourly_cisd_in_candle(seg, seg.index[0], seg.index[-1], r[direction_col],
                                   scope=scope, level_rule="series_open",
                                   htf_open=float(r["open"]))
        out[k] = ev is not None
    return out


def c2c3_h1_bias(m1: pd.DataFrame, scope: str = "range",
                 c3_reference: str = "c2_open") -> pd.DataFrame:
    """Spec §2.4: daily C2 or C3 closure PLUS an hourly CISD in the same direction inside
    that day. One row per completed (non-stub) day with columns open/high/low/close,
    close_time, closure, closure_kind, h1_cisd (bool), bias ('bullish'/'bearish'/'none').
    The bias is for the NEXT trading day; it is knowable at this day's close_time."""
    d = daily(m1)
    h = cl.build_bars(m1, "1h")
    cls = daily_closures(d[OHLC], c3_reference=c3_reference)
    d = d.join(cls[["closure", "closure_kind"]])
    cand = d[d["closure"] != "none"]
    conf = ltf_cisd_inside(d, h, cand.assign(direction=cand["closure"]), scope=scope)
    d["h1_cisd"] = False
    d.loc[cand.index[conf], "h1_cisd"] = True
    d["bias"] = np.where(d["h1_cisd"], d["closure"], "none")
    return d


def engine_bias(bars: pd.DataFrame) -> pd.DataFrame:
    """Spec §2.3 previous-candle engine on any candle frame: implied bias for the NEXT
    candle (continuation closure -> same way, reversal closure -> opposite, both sides
    -> none, inside -> trend, range-bound -> none)."""
    st = previous_candle_state(bars[OHLC])
    out = bars.copy()
    out["state"] = st["state"]
    out["bias"] = st["implied_bias"]
    return out


def next_candle_draw_events(b: pd.DataFrame) -> pd.DataFrame:
    """Trade the candle after a biased candle D toward D's bias-side extreme (the draw),
    stop at D's opposite extreme. Decided at D's close_time."""
    x = b[b["bias"].isin(["bullish", "bearish"])]
    bull = (x["bias"] == "bullish").to_numpy()
    ct = pd.DatetimeIndex(x["close_time"])
    return pd.DataFrame({
        "decision_time": ct, "available_at": ct,
        "direction": np.where(bull, 1, -1),
        "stop_px": np.where(bull, x["low"], x["high"]).astype(float),
        "target_px": np.where(bull, x["high"], x["low"]).astype(float),
    })


def day_end_utc(tday: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """17:00 NY at the end of trading day `tday` (naive date of the 18:00 roll)."""
    loc = pd.DatetimeIndex(tday) + pd.Timedelta(days=1, hours=17)
    return loc.tz_localize(NY).tz_convert("UTC")


def hourly_with_prior_day(m1: pd.DataFrame, bias_days: pd.DataFrame) -> pd.DataFrame:
    """1h bars annotated with the most recent COMPLETED bias-source day (via cl.asof on
    its close_time <= the 1h bar's START), the current day's open and running extremes
    through the bar (closed 1h bars only), and NY clock of the bar close."""
    h = cl.build_bars(m1, "1h")
    h = h[OHLC + ["close_time"]].copy()
    td = cl.trading_day(h.index)
    h["tday"] = td
    g = h.groupby("tday", sort=False)
    h["day_open"] = g["open"].transform("first")
    h["run_high"] = g["high"].cummax()
    h["run_low"] = g["low"].cummin()
    prev = cl.asof(bias_days[["open", "high", "low", "close", "bias", "close_time",
                                "trading_day"]], h.index)
    for c in ("open", "high", "low", "close", "bias", "close_time"):
        h["D_" + c] = prev[c].to_numpy()
    h["D_tday"] = pd.DatetimeIndex(prev["trading_day"]) if "trading_day" in prev else pd.NaT
    ny = cl.to_ny(pd.DatetimeIndex(h["close_time"]))
    h["ny_close_min"] = ny.hour * 60 + ny.minute
    h["day_end"] = day_end_utc(pd.DatetimeIndex(td))
    # the prior day must be the immediately preceding session (<= 4 calendar days back
    # covers weekends/holidays; anything older is a data hole, not "yesterday")
    gap = (pd.DatetimeIndex(td) - pd.DatetimeIndex(h["D_tday"])).days
    h["D_ok"] = (gap >= 1) & (gap <= 4)
    return h


def in_ny_close_window(minutes: np.ndarray, start_hhmm: str, end_hhmm: str) -> np.ndarray:
    """1h-bar CLOSE time inside [start, end] NY, window may wrap midnight."""
    s = int(start_hhmm[:2]) * 60 + int(start_hhmm[3:])
    e = int(end_hhmm[:2]) * 60 + int(end_hhmm[3:])
    if s <= e:
        return (minutes >= s) & (minutes <= e)
    return (minutes >= s) | (minutes <= e)


def intraday_bias_book(m1: pd.DataFrame, win: tuple[str, str]) -> pd.DataFrame:
    """Baseline book for the intraday gate tests: on the session AFTER a confirmed daily
    bias (daily C2/C3 + H1 CISD, c2c3_h1_bias), at every 1h close whose NY close time is
    inside `win`, go in the bias direction toward the prior day's bias-side extreme (the
    draw), stop at the current day's running opposite extreme (the level being traded
    away from), exit at 17:00 NY. Rows where the draw is already reached, the target is
    not beyond price, or the stop is closer than MIN_RISK_FRAC x prior-day range are
    dropped. Carries the columns the gates need (prefixed x_)."""
    bd = c2c3_h1_bias(m1)
    h = hourly_with_prior_day(m1, bd)
    sel = (h["D_ok"].to_numpy() & h["D_bias"].isin(["bullish", "bearish"]).to_numpy()
           & in_ny_close_window(h["ny_close_min"].to_numpy(), *win))
    x = h[sel].copy()
    bull = (x["D_bias"] == "bullish").to_numpy()
    sgn = np.where(bull, 1.0, -1.0)
    c = x["close"].to_numpy(float)
    stop = np.where(bull, x["run_low"], x["run_high"]).astype(float)
    tgt = np.where(bull, x["D_high"], x["D_low"]).astype(float)
    spent = np.where(bull, x["run_high"] >= x["D_high"], x["run_low"] <= x["D_low"])
    rng = (x["D_high"] - x["D_low"]).to_numpy(float)
    risk = sgn * (c - stop)
    tdist = sgn * (tgt - c)
    ct = pd.DatetimeIndex(x["close_time"])
    hold = pd.DatetimeIndex(x["day_end"]) - ct
    ok = (~spent) & (risk >= MIN_RISK_FRAC * rng) & (tdist > 0) & (hold > pd.Timedelta(0))
    out = pd.DataFrame({
        "decision_time": ct, "available_at": ct, "direction": sgn.astype(int),
        "stop_px": stop, "target_px": tgt, "max_hold": hold,
        "x_bar_start": x.index, "x_tday": pd.DatetimeIndex(x["tday"]),
        "x_day_open": x["day_open"].to_numpy(float), "x_close": c,
        "x_run_high": x["run_high"].to_numpy(float), "x_run_low": x["run_low"].to_numpy(float),
    })
    return out[ok].reset_index(drop=True)
