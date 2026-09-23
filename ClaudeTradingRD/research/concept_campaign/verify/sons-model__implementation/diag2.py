import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
ev = pd.read_parquet("orig_events.parquet")
h = cl.to_ny(ev.decision_time).dt.hour if hasattr(cl.to_ny(ev.decision_time),'dt') else pd.DatetimeIndex(cl.to_ny(ev.decision_time)).hour
share = pd.Series(np.asarray(h)).value_counts(normalize=True).sort_index()
m1 = cl.load_m1(); mh = pd.Series(pd.DatetimeIndex(cl.to_ny(pd.Series(m1.index))).hour).value_counts(normalize=True).sort_index()
print(pd.DataFrame({"events": share, "m1": mh, "ratio": share/mh}).round(3).to_string())
res = cl.trade_test(ev, max_hold="150min", keep_trades=True); tr = res["_trades"]
print("risk $ quantiles", tr.risk.quantile([.1,.25,.5,.75,.9]).round(2).to_dict())
print("risk / entry bp median", (tr.risk/tr.entry*1e4).median())
tr["yr"] = pd.DatetimeIndex(tr.decision_time).year
tr["d"] = tr.net_R - tr.ctrl_mean_R
print(tr.groupby("yr").agg(n=("d","size"), diff=("d","mean"), risk=("risk","median")).round(3))
