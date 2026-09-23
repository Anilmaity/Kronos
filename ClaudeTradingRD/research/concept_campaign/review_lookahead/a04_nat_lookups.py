"""A NaT in `times` (e.g. an unmatched join / a condition that never fired) makes the
availability-safe lookups return the LAST row of the whole dataset (2026) instead of NaN."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
t = pd.DatetimeIndex([pd.Timestamp("2018-03-07 15:00", tz="UTC"), pd.NaT]).tz_convert("UTC")
d = cl.bars("1D")
print("asof(1D) ->\n", cl.asof(d, t)[["high", "low", "available_at", "bar_start"]])
print("prior_hilo(1D) ->\n", cl.prior_hilo(t, "1D")[["high", "low", "available_at"]])
print("prior_hilo(ny_am window) ->\n", cl.prior_hilo(t, "ny_am")[["high", "low", "available_at"]])
print("open_at(00:00) ->\n", cl.open_at(t, "00:00"))
print("running_hilo(1W) ->\n", cl.running_hilo(t, "1W"))
