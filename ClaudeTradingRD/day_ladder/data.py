"""Shared loader: ~16 months of XAU_USD M1 mid bars (UTC), stitched from the two OANDA caches."""
import pandas as pd

def load_m1():
    a = pd.read_parquet("../xau_m1_oanda.parquet")[["time", "open", "high", "low", "close"]]
    b = pd.read_parquet("../xm_real/xau_m1_2026-07-16_now_mba.parquet")[["time", "open", "high", "low", "close"]]
    d = pd.concat([a[a.time < b.time.min()], b]).drop_duplicates("time").sort_values("time").set_index("time")
    return d.astype(float)

def atr(d, n):  # ATR in points on closed bars
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()
