"""Shared helpers for batch liquidity_own_02b (not a concept script).

Correlated-asset H1 series for the SMT concepts. XAU_EUR and XAU_GBP H1 were fetched
from OANDA practice (mid prices, complete candles only) on 2026-09-23 with the
unmodified `fetch_correlated.fetch_candles`, 2015-12-01 -> 2026-07-24, into ./data/.
XAG_USD H1 is the project's existing m3_scalper/xag_h1_full.parquet (from 2010-01-03).
All are left-labelled UTC hourly bars, the same convention as cl.build_bars(m1, "1h").
A correlate bar is only ever read at a gold bar's label, and every use is decided at or
after that gold bar's close_time, so the correlate adds no information beyond that close.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CORR_FILES = {
    "xau_eur": HERE / "data" / "xau_eur_h1.parquet",
    "xau_gbp": HERE / "data" / "xau_gbp_h1.parquet",
    "xag_usd": HERE.parents[3] / "m3_scalper" / "xag_h1_full.parquet",
}
_CORR: dict = {}


def corr_h1(name: str) -> pd.DataFrame:
    if name not in _CORR:
        df = pd.read_parquet(CORR_FILES[name])[["open", "high", "low", "close"]]
        df.index = pd.DatetimeIndex(df.index).tz_convert("UTC")
        _CORR[name] = df.sort_index()
    return _CORR[name]


def aligned(name: str, index: pd.DatetimeIndex) -> pd.DataFrame:
    """Correlate H1 bars re-indexed to gold 1h bar labels (NaN where missing)."""
    return corr_h1(name).reindex(pd.DatetimeIndex(index))


def swings(df: pd.DataFrame, left: int = 2, right: int = 2):
    """Vectorised 2/2 fractal swings, identical to detectors.primitives.swing_points:
    high[i] > the `left` prior highs and >= the `right` following highs. Returns
    (is_high, is_low) bool arrays indexed by the swing bar; confirmed at bar i+right."""
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    n = len(h)
    is_h = np.zeros(n, bool)
    is_l = np.zeros(n, bool)
    if n < left + right + 1:
        return is_h, is_l
    ih = np.ones(n - left - right, bool)
    il = np.ones(n - left - right, bool)
    c = slice(left, n - right)
    for k in range(1, left + 1):
        ih &= h[c] > h[left - k:n - right - k]
        il &= l[c] < l[left - k:n - right - k]
    for k in range(1, right + 1):
        ih &= h[c] >= h[left + k:n - right + k]
        il &= l[c] <= l[left + k:n - right + k]
    is_h[c] = ih
    is_l[c] = il
    return is_h, is_l


def last_confirmed_level(is_sw: np.ndarray, px: np.ndarray, right: int = 2):
    """For each bar j: the price of the most recent swing whose confirmation bar
    (swing index + right) is <= j - 1, i.e. known at the close of bar j-1, so it can
    be compared with bar j. Also returns that swing's index (-1 if none)."""
    n = len(px)
    conf = np.full(n, -1)
    idx = np.flatnonzero(is_sw)
    cbar = idx + right                      # the bar at whose close it is confirmed
    ok = cbar < n
    # swing known for bar j if cbar <= j-1
    last = np.full(n, -1)
    if ok.any():
        marks = np.full(n, -1)
        marks[cbar[ok]] = idx[ok]
        s = pd.Series(marks).replace(-1, np.nan).ffill().to_numpy()
        # shift by one: bar j uses swings confirmed by close of j-1
        s = np.concatenate([[np.nan], s[:-1]])
        last = np.where(np.isnan(s), -1, s).astype(int)
    lvl = np.where(last >= 0, px[np.maximum(last, 0)], np.nan)
    return lvl, last
