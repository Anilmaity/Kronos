"""Shared, pure helpers for batch structure_own_05a (structure, TTrades own voice).

Correlates (the only non-gold series the campaign holds; all OANDA practice feed):
  XAG_USD H1  m3_scalper/xag_h1_full.parquet  (2010-01-03 -> 2026-07-23)
  EUR_USD H1  m3_scalper/eur_h1_full.parquet  (2010-01-03 -> 2026-07-23)
Every function takes a gold M1 slice; correlate bars are cut to those whose nominal
close (start + 1h) is <= the slice's last M1 close, so `probe_lookahead` sees exactly
what a live reader would have seen.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

RD = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD")
PATHS = {"xag": RD / "m3_scalper" / "xag_h1_full.parquet",
         "eur": RD / "m3_scalper" / "eur_h1_full.parquet"}
H1 = pd.Timedelta(hours=1)
OHLC = ["open", "high", "low", "close"]
_RAW: dict = {}


def raw_h1(name: str) -> pd.DataFrame:
    if name not in _RAW:
        x = pd.read_parquet(PATHS[name])
        if "time" in x.columns:
            x = x.set_index("time")
        x.index = pd.to_datetime(x.index, utc=True)
        x = x[OHLC].astype("float64").sort_index()
        _RAW[name] = x[~x.index.duplicated(keep="first")]
    return _RAW[name]


def corr_h1(name: str, m1: pd.DataFrame, drop_halt_hour: bool = False,
            cut: str = "closed") -> pd.DataFrame:
    """Correlate H1 bars that had CLOSED by the slice's last M1 close.

    drop_halt_hour: drop correlate bars starting at 17:00 NY (gold's daily halt hour). Such a
    bar closes at 18:00 NY, after gold's last M1 close of the day, so a reader at the gold
    day close could not have seen it on a cut (probe) yet would on the full file.
    cut="closed": bars whose end <= the slice's last M1 close (strict; misfires when the
    slice's last gold minute is missing just before the halt). cut="gold_last": bars
    starting no later than the hour of the slice's last M1 - safe ONLY for detectors whose
    events are stamped at the close of the gold period containing that bar (a daily
    detector deciding at the gold day close), never earlier."""
    x = raw_h1(name)
    if drop_halt_hour:
        x = x[x.index.tz_convert("America/New_York").hour != 17]
    last_close = pd.DatetimeIndex(m1.index).tz_convert("UTC")[-1] + pd.Timedelta(minutes=1)
    first = pd.DatetimeIndex(m1.index).tz_convert("UTC")[0].floor("h") - pd.Timedelta(days=3)
    if cut == "closed":
        return x[(x.index >= first) & (x.index + H1 <= last_close)]
    last_start = pd.DatetimeIndex(m1.index).tz_convert("UTC")[-1].floor("h")
    return x[(x.index >= first) & (x.index <= last_start)]


def daily_from_h1(x: pd.DataFrame) -> pd.DataFrame:
    """Daily OHLC on the 18:00-NY trading day from H1 bars; close_time = last H1 end."""
    td = cl.trading_day(x.index)
    g = x.assign(_end=x.index + H1).groupby(td, sort=True)
    d = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                      "low": g["low"].min(), "close": g["close"].last(),
                      "close_time": g["_end"].max(), "n_h1": g["open"].size()})
    d.index.name = "trading_day"
    return d


def ratio_daily(num: pd.DataFrame, den: pd.DataFrame) -> pd.DataFrame:
    """Daily OHLC of a ratio LINE (num close / den close on shared H1 starts):
    open = first hourly ratio close, high/low = extreme hourly ratio closes, close = last.
    close_time = the later of the two series' last H1 end that day."""
    j = num[["close"]].join(den[["close"]], how="inner", lsuffix="_n", rsuffix="_d")
    r = pd.DataFrame({"open": j["close_n"] / j["close_d"]}, index=j.index)
    r["high"] = r["low"] = r["close"] = r["open"]
    return daily_from_h1(r)


def closure_class(d: pd.DataFrame) -> pd.Series:
    """Previous-candle engine (method_spec §2.3) on a daily frame: +1 when the candle
    closes ABOVE the previous candle's high, -1 when it closes BELOW the previous low,
    0 otherwise (closed inside = consolidating / no directional read)."""
    ph, pl = d["high"].shift(1), d["low"].shift(1)
    c = d["close"]
    out = np.where(c > ph, 1, np.where(c < pl, -1, 0))
    out = np.where(ph.isna(), 0, out)
    return pd.Series(out.astype(int), index=d.index)


def asof_rows(d: pd.DataFrame, t) -> np.ndarray:
    """Row position of the last row of d (sorted by close_time) with close_time <= t; -1 if none."""
    ct = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC").as_unit("ns").asi8
    tn = pd.DatetimeIndex(t).tz_convert("UTC").as_unit("ns").asi8
    return np.searchsorted(ct, tn, side="right") - 1


def atr(b: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = b["close"].shift(1)
    tr = pd.concat([b["high"] - b["low"], (b["high"] - pc).abs(),
                    (b["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def summary(res: dict) -> str:
    keys = ("test_type", "verdict", "verdict_detail", "n", "n_complement", "gate_firing_rate",
            "avg_R", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "ties",
            "ctrl_overlap", "exposure_bars", "halves", "dependence")
    out = []
    for k in keys:
        if k in res:
            v = res[k]
            if isinstance(v, float):
                v = round(v, 4)
            out.append(f"  {k}: {v}")
    return "\n".join(out)
