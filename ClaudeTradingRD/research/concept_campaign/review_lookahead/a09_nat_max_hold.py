"""A NaN/NaT in a per-row max_hold column is not rejected: under hold_basis='clock' the
trade is held until stop/target or the END OF THE DATA (years)."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
b = cl.bars("1h"); b = b[b.index >= "2017-01-01"].iloc[:400]
ct = pd.DatetimeIndex(b.close_time)
hold = pd.Series([pd.Timedelta("2h")] * len(ct)); hold.iloc[::2] = pd.NaT
ev = pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 1,
                   "stop_dist": 1000.0, "rr": np.nan, "max_hold": hold.to_numpy()})
r = cl.trade_test(ev, keep_trades=True)
tr = r["_trades"]
dur = (pd.DatetimeIndex(tr.exit_time) - pd.DatetimeIndex(tr.entry_time))
print("n:", r["n"], "dropped:", r["dropped"])
print("hold durations (days) for NaT rows:", dur[::2].days.min(), "..", dur[::2].days.max())
print("exposure_bars:", r["exposure_bars"], "avg_R:", round(r["avg_R"], 3))
