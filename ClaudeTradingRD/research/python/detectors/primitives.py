"""Primitive detectors shared by most ICT/SMC concepts.

Deliberately small and boring. These are the building blocks that concept-level
detectors compose; keeping them separate means a concept detector can be wrong
without the primitives being in doubt.

Every function takes an OHLC DataFrame with a DatetimeIndex (see bars.py) and
returns either a boolean Series aligned to that index or a DataFrame of events.
No function looks ahead: an event stamped at bar i uses only bars <= i. That
matters because a look-ahead primitive would make every downstream backtest
silently optimistic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ── swing points ──────────────────────────────────────────────────────────────
def swing_points(df: pd.DataFrame, left: int = 2, right: int = 2
                 ) -> pd.DataFrame:
    """Fractal swing highs/lows.

    A swing high at i requires high[i] to be strictly greater than the `left`
    highs before it and >= the `right` highs after it. Confirmation therefore
    arrives `right` bars late; `confirmed_at` records when the point could first
    have been known, so callers never trade a swing before it existed.
    """
    if left < 1 or right < 1:
        raise ValueError("left and right must be >= 1")
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    n = len(df)
    is_h = np.zeros(n, dtype=bool)
    is_l = np.zeros(n, dtype=bool)
    for i in range(left, n - right):
        wh, wl = h[i], l[i]
        if (h[i - left:i] < wh).all() and (h[i + 1:i + 1 + right] <= wh).all():
            is_h[i] = True
        if (l[i - left:i] > wl).all() and (l[i + 1:i + 1 + right] >= wl).all():
            is_l[i] = True
    idx = df.index
    out = pd.DataFrame(
        {"swing_high": is_h, "swing_low": is_l,
         "high": df["high"].to_numpy(), "low": df["low"].to_numpy()},
        index=idx)
    pos = np.arange(n)
    ok = (is_h | is_l) & (pos + right < n)
    # Build with the index's own dtype so a tz-aware index does not get assigned
    # into a tz-naive column (pandas raises rather than coercing).
    confirmed = pd.Series(pd.NaT, index=idx, dtype=idx.dtype)
    if ok.any():
        confirmed.iloc[pos[ok]] = idx[pos[ok] + right]
    out["confirmed_at"] = confirmed
    return out


# ── sweeps ────────────────────────────────────────────────────────────────────
def sweep_of_level(df: pd.DataFrame, level: float, side: str,
                   require_close_back: bool = True) -> pd.Series:
    """Bars that sweep `level`.

    side='buy_side'  -> price trades ABOVE level (taking buy-side liquidity)
    side='sell_side' -> price trades BELOW level

    With require_close_back=True the bar must also close back on the original
    side, which is what distinguishes a *sweep* (rejection) from an *expansion*
    (acceptance). That distinction is load-bearing all over this methodology.
    """
    if side not in ("buy_side", "sell_side"):
        raise ValueError("side must be 'buy_side' or 'sell_side'")
    if side == "buy_side":
        pierced = df["high"] > level
        closed_back = df["close"] <= level
    else:
        pierced = df["low"] < level
        closed_back = df["close"] >= level
    return (pierced & closed_back) if require_close_back else pierced


def candle_range_sweep(df: pd.DataFrame) -> pd.DataFrame:
    """Candle-Range-Theory style C1/C2 on the given timeframe.

    For each bar i (as C2) against bar i-1 (as C1):
      swept_high : C2.high > C1.high and C2.close <= C1.high
      swept_low  : C2.low  < C1.low  and C2.close >= C1.low
      both       : both sides taken (a 'seek and destroy' shaped candle)
      expansion  : pierced a side and CLOSED beyond it (not a sweep)

    Returns a frame aligned to df with those boolean columns plus the C1 range,
    so a caller can compute targets (e.g. the opposite extreme, or 50%).
    """
    c1_h = df["high"].shift(1)
    c1_l = df["low"].shift(1)
    close = df["close"]

    swept_high = (df["high"] > c1_h) & (close <= c1_h)
    swept_low = (df["low"] < c1_l) & (close >= c1_l)
    exp_up = (df["high"] > c1_h) & (close > c1_h)
    exp_dn = (df["low"] < c1_l) & (close < c1_l)

    out = pd.DataFrame({
        "c1_high": c1_h, "c1_low": c1_l,
        "c1_mid": (c1_h + c1_l) / 2.0,
        "swept_high": swept_high.fillna(False),
        "swept_low": swept_low.fillna(False),
        "swept_both": (swept_high & swept_low).fillna(False),
        "expansion_up": exp_up.fillna(False),
        "expansion_down": exp_dn.fillna(False),
    }, index=df.index)
    out["inside_bar"] = ((df["high"] <= c1_h) & (df["low"] >= c1_l)).fillna(False)
    return out


# ── displacement / gaps ───────────────────────────────────────────────────────
def fair_value_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """Three-bar fair value gaps, stamped on the THIRD bar (when it is known).

    Bullish FVG: low[i] > high[i-2]  -> gap (high[i-2], low[i])
    Bearish FVG: high[i] < low[i-2]  -> gap (high[i], low[i-2])
    """
    h2, l2 = df["high"].shift(2), df["low"].shift(2)
    bull = df["low"] > h2
    bear = df["high"] < l2
    out = pd.DataFrame(index=df.index)
    out["bullish_fvg"] = bull.fillna(False)
    out["bearish_fvg"] = bear.fillna(False)
    out["gap_low"] = np.where(bull, h2, np.where(bear, df["high"], np.nan))
    out["gap_high"] = np.where(bull, df["low"], np.where(bear, l2, np.nan))
    out["gap_size"] = out["gap_high"] - out["gap_low"]
    return out


def displacement(df: pd.DataFrame, lookback: int = 20, mult: float = 2.0
                 ) -> pd.Series:
    """Bars whose body exceeds `mult` x the trailing mean body.

    The trailing window EXCLUDES the current bar (shift(1)), otherwise a large
    bar inflates its own benchmark and the test becomes self-defeating.
    """
    body = (df["close"] - df["open"]).abs()
    base = body.shift(1).rolling(lookback, min_periods=lookback).mean()
    return (body > mult * base).fillna(False)
