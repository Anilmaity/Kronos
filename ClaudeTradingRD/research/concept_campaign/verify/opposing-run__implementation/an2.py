import pandas as pd, numpy as np
tr=pd.read_pickle("trades.pkl"); tr["adj"]=tr.net_R-tr.ctrl_mean_R
print(tr.groupby(["gate","direction"])[["net_R","ctrl_mean_R","adj"]].agg(["mean","count"]).round(3))
tr["hr"]=tr.decision_time.dt.tz_convert("America/New_York").dt.hour
print(tr.groupby(["hr","gate"])[["net_R","ctrl_mean_R","adj"]].mean().unstack().round(3))
tr["yr"]=tr.decision_time.dt.year
t=tr.groupby(["yr","gate"]).adj.mean().unstack(); t["d"]=t[True]-t[False]; print(t.round(3))
# raw diff CI day-block quick
tr["day"]=tr.decision_time.dt.tz_convert("America/New_York").dt.date
rng=np.random.default_rng(0); days=tr.day.unique()
def stat(df,col): return df[df.gate][col].mean()-df[~df.gate][col].mean()
print("raw diff",stat(tr,"net_R"),"adj diff",stat(tr,"adj"))
grp={d:x for d,x in tr.groupby("day")}
bs=[]
for i in range(1000):
    s=rng.choice(days,len(days)); df=pd.concat([grp[d] for d in s]); bs.append((stat(df,"net_R"),stat(df,"adj")))
bs=np.array(bs); print("raw CI",np.percentile(bs[:,0],[2.5,97.5]),"adj CI",np.percentile(bs[:,1],[2.5,97.5]))
