"""Shared helpers for batch structure_own_04b (TTrades own voice, structure).

Everything is PURE in the gold M1 frame it is given (the probe truncates M1 and
re-runs the detector). The silver correlate (OANDA XAG_USD H1, m3_scalper/xag_h1_full.parquet,
the file phase 3 used for correlates) is inner-joined on the gold H1 labels built from that
frame, so truncating M1 truncates the correlate too. Every event is stamped at a bar close.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from concept_lab.data import utc_ns  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

RD = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD")
H1 = pd.Timedelta(hours=1)

# phase-3 locked rung-0 CISD config (meta/conjunction_preregistration.md)
CISD = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
RR = 2.0
HOLD = {"1min": "10min", "5min": "50min", "15min": "150min", "1h": "10h"}   # 10 entry-TF periods

_RAW: dict = {}


def cisd_frame(m1: pd.DataFrame, tf: str):
    """(bars, cisd events, base events frame) for the rung-0 CISD book on `tf`."""
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], **CISD)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"]).tz_convert("UTC")
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": RR})
    return b, ev.reset_index(drop=True), out


def atr(b: pd.DataFrame, n: int = 14) -> np.ndarray:
    """Simple-mean ATR(n) through each bar (inclusive), from that frame only."""
    h, l, c = b["high"].to_numpy(float), b["low"].to_numpy(float), b["close"].to_numpy(float)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


def silver_raw() -> pd.DataFrame:
    if "xag" not in _RAW:
        x = pd.read_parquet(RD / "m3_scalper" / "xag_h1_full.parquet")
        if "time" in x.columns:
            x = x.set_index("time")
        x.index = pd.to_datetime(x.index, utc=True)
        _RAW["xag"] = x[["open", "high", "low", "close"]].astype("float64").sort_index()
    return _RAW["xag"]


def pair_h1(m1: pd.DataFrame) -> pd.DataFrame:
    """Gold 1h bars (g_*) inner-joined with silver H1 (s_*) on gold's labels.

    The correlate is cut to bars that closed by the end of the gold slice.
    """
    g = cl.build_bars(m1, "1h")
    cutoff = m1.index[-1] + pd.Timedelta(minutes=1)
    s = silver_raw()
    s = s[s.index + H1 <= cutoff + H1]           # never beyond gold's own last (possibly partial) bar
    idx = g.index.intersection(s.index)
    G, S = g.loc[idx], s.loc[idx]
    out = pd.DataFrame({"g_open": G.open, "g_high": G.high, "g_low": G.low, "g_close": G.close,
                        "s_open": S.open, "s_high": S.high, "s_low": S.low, "s_close": S.close,
                        "close_time": G.close_time}, index=idx)
    return out


def last_before(src_times, src_vals, t):
    """Value of the latest src row with src_time <= t (NaN if none). Times tz-aware."""
    st, tt = utc_ns(src_times), utc_ns(t)
    k = np.searchsorted(st, tt, side="right") - 1
    ok = k >= 0
    out = np.full(len(tt), np.nan)
    out[ok] = np.asarray(src_vals, float)[k[ok]]
    return out
