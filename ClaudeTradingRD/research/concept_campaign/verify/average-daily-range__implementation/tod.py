import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import pandas as pd, numpy as np
tr = pd.read_pickle("trades.pkl")
ny = pd.DatetimeIndex(tr.decision_time).tz_convert("America/New_York")
tr["h"] = ny.hour
tr["adj"] = tr.net_R - tr.ctrl_mean_R
tr["gap_entry"] = (pd.DatetimeIndex(tr.entry_time) - pd.DatetimeIndex(tr.decision_time)) > pd.Timedelta("5min")
print(tr.groupby("gate").agg(n=("adj","size"), adj=("adj","mean"), net=("net_R","mean"), gapfrac=("gap_entry","mean")))
t = tr.groupby(["h","gate"]).agg(n=("adj","size"), adj=("adj","mean")).unstack()
print(t.to_string())
print("excluding gap entries:")
x = tr[~tr.gap_entry]
a = x.groupby("gate").adj.mean(); print(a, a[True]-a[False])
# hour-stratified diff (weight by complement counts)
s = tr.groupby(["h","gate"]).adj.mean().unstack().dropna()
w = tr[~tr.gate].groupby("h").size().reindex(s.index)
print("hour-stratified diff (complement-weighted):", ((s[True]-s[False])*w).sum()/w.sum())
