import pandas as pd, numpy as np
tr=pd.read_pickle("trades.pkl")
tr["adj"]=tr.net_R-tr.ctrl_mean_R
tr["riskpct"]=tr.risk/tr.entry*100
g=tr.groupby("gate")
print(g[["net_R","gross_R","ctrl_mean_R","adj","risk","riskpct"]].mean())
print(g.reason.value_counts(normalize=True))
tr["rq"]=pd.qcut(tr.riskpct,5,labels=False)
print(tr.groupby(["rq","gate"])[["net_R","ctrl_mean_R","adj"]].agg(["mean","count"]).round(3))
# exit reason for ctrl unknown; look at net_R dist
print(g.net_R.describe())
