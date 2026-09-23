import pandas as pd, numpy as np
tr = pd.read_pickle("trades_a.pkl")
tr["d"] = tr.net_R - tr.ctrl_mean_R
tr["yr"] = pd.DatetimeIndex(tr.decision_time).year
tr["tr"] = (tr.target-tr.entry).abs()/tr.risk
print(tr.groupby("yr").agg(risk_med=("risk","median"), rr_med=("tr","median"), d=("d","mean")).round(3))
tr["rq"] = tr.groupby("yr")["risk"].transform(lambda x: pd.qcut(x,5,labels=False))
print(tr.pivot_table(index="yr", columns="rq", values="d", aggfunc="mean").round(3))
tr["side"]=tr.direction
print(tr.pivot_table(index="yr", columns="side", values="d", aggfunc="mean").round(3))
# small-risk share absolute $
print(tr.assign(small=tr.risk<0.3).pivot_table(index="yr", columns="small", values="d", aggfunc=["mean","count"]).round(3))
