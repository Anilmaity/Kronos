import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
o = pd.read_parquet("orig_events.parquet"); e = pd.read_parquet("indep_events.parquet")
C=["decision_time","available_at","direction","stop_px","rr"]
ro = cl.trade_test(o[C], max_hold="150min", keep_trades=True, n_boot=500)["_trades"]
re_ = cl.trade_test(e[C], max_hold="150min", keep_trades=True, n_boot=500)["_trades"]
for nm,t in (("orig",ro),("indep",re_)):
    print(nm, len(t), "real", t.net_R.mean().round(4), "ctrl", t.ctrl_mean_R.mean().round(4))
ko = set(zip(ro.decision_time, ro.direction))
t = re_.copy(); t["in_o"] = [ (a,b) in ko for a,b in zip(t.decision_time,t.direction)]
print(t.groupby("in_o")[["net_R","ctrl_mean_R"]].agg(["mean","count"]))
x = e.merge(o, on=["decision_time","direction"], how="left", indicator=True)
ex = x[x._merge=="left_only"]
print(pd.DatetimeIndex(ex.decision_time).dayofweek.value_counts())
