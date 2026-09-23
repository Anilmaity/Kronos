import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
t = pd.read_pickle("trades_orig.pkl"); print(t.columns.tolist()); 
a = pd.read_pickle("allc2_orig.pkl"); a = a[a.conf & a.posok]
h = cl.to_ny(pd.DatetimeIndex(a.decision_time)).hour
print(pd.Series(h).value_counts().sort_index())
t["h"] = cl.to_ny(pd.DatetimeIndex(t.decision_time)).hour
t["d"] = t.net_R - t.ctrl_mean_R
print(t.groupby("h").agg(n=("d","size"), diff=("d","mean"), real=("net_R","mean"), ctrl=("ctrl_mean_R","mean")).round(3))
