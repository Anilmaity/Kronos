"""Bar-series utilities for testing concept detectors against real XAUUSD data.

The corpus concepts are only worth recording if they are decidable on a chart,
so every detector is expected to run against a real OHLC series. This module is
the shared substrate: load M1, resample to any timeframe, and slice sessions.

Data source: ClaudeTradingRD/m3_scalper/xau_m1_3y.parquet (~1.07M M1 bars,
tz-aware UTC). Nothing here reaches the network.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RD_ROOT = Path(__file__).resolve().parents[2]      # ...\ClaudeTradingRD
M1_PARQUET = RD_ROOT / "m3_scalper" / "xau_m1_3y.parquet"
ALT_PARQUET = RD_ROOT / "xau_m1_oanda.parquet"

OHLC = {"open": "first", "high": "max", "low": "min", "close": "last"}


def load_m1(path: Path | str | None = None) -> pd.DataFrame:
    """M1 OHLC indexed by tz-aware UTC DatetimeIndex, sorted, deduplicated."""
    p = Path(path) if path else (M1_PARQUET if M1_PARQUET.exists() else ALT_PARQUET)
    if not p.exists():
        raise FileNotFoundError(f"no M1 parquet at {p}")
    df = pd.read_parquet(p)
    if "time" in df.columns:
        df = df.set_index("time")
    df.index = pd.to_datetime(df.index, utc=True)
    df = df[["open", "high", "low", "close"]].astype("float64")
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Resample an OHLC frame to `tf` (pandas offset alias: '5min','1h','1D',...).

    Empty buckets (weekends, holidays, gaps) are dropped rather than forward
    filled: a synthetic flat bar would invent a candle that never traded, and
    candle-based concepts like CRT would then fire on fabricated ranges.
    """
    out = df.resample(tf, label="left", closed="left").agg(OHLC)
    return out.dropna(subset=["open", "high", "low", "close"])


def session(df: pd.DataFrame, start: str, end: str, tz: str = "America/New_York"
            ) -> pd.DataFrame:
    """Rows whose local wall-clock time falls in [start, end) e.g. '09:30','10:00'.

    A timezone must be explicit. The corpus repeatedly gives session times with
    no timezone stated, which is recorded as an ambiguity in the concept files —
    this function forces the caller to commit to one rather than guess silently.
    """
    local = df.index.tz_convert(tz)
    t = pd.Series(local.time, index=df.index)
    lo = pd.Timestamp(start).time()
    hi = pd.Timestamp(end).time()
    mask = (t >= lo) & (t < hi) if lo <= hi else (t >= lo) | (t < hi)
    return df[mask.values]


def add_session_date(df: pd.DataFrame, tz: str = "America/New_York") -> pd.DataFrame:
    """Add a `session_date` column = local calendar date, for per-day grouping."""
    out = df.copy()
    out["session_date"] = df.index.tz_convert(tz).date
    return out


def describe(df: pd.DataFrame) -> str:
    return (f"{len(df):,} bars  {df.index.min()} -> {df.index.max()}  "
            f"cols={list(df.columns)}")


if __name__ == "__main__":
    m1 = load_m1()
    print("M1  ", describe(m1))
    for tf in ("5min", "15min", "1h", "4h", "1D"):
        print(f"{tf:5}", describe(resample(m1, tf)))
