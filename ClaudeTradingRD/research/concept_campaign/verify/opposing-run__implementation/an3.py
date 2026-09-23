import pandas as pd, numpy as np
tr=pd.read_pickle("trades.pkl"); tr["adj"]=tr.net_R-tr.ctrl_mean_R
ev=pd.read_pickle("indep_ev.pkl"); tr=tr.merge(ev[["decision_time","ratio"]],on="decision_time")
print(tr.groupby(["gate","direction"])[["net_R","ctrl_mean_R","adj"]].agg(["mean","count"]).round(3))
tr["hr"]=tr.decision_time.dt.tz_convert("America/New_York").dt.hour
print(tr.groupby(["hr","gate"])[["net_R","ctrl_mean_R","adj"]].mean().unstack().round(3))
tr["yr"]=tr.decision_time.dt.year
t=tr.groupby(["yr","gate"]).adj.mean().unstack(); t["d"]=t[True]-t[False]; print(t.round(3))
tr["day"]=pd.factorize(tr.decision_time.dt.tz_convert("America/New_York").dt.date)[0]
nd=tr.day.max()+1; rng=np.random.default_rng(0)
def boot(col,mask):
    g=mask.astype(float); v=tr[col].to_numpy()
    sg=np.bincount(tr.day,v*g,nd); cg=np.bincount(tr.day,g,nd); sc=np.bincount(tr.day,v*(1-g),nd); cc=np.bincount(tr.day,1-g,nd)
    pt=sg.sum()/cg.sum()-sc.sum()/cc.sum()
    w=rng.multinomial(nd,np.ones(nd)/nd,size=2000)
    bs=(w@sg)/(w@cg)-(w@sc)/(w@cc)
    return round(pt,4), np.round(np.percentile(bs,[2.5,97.5]),4)
print("raw", boot("net_R",tr.gate.to_numpy())); print("adj", boot("adj",tr.gate.to_numpy())); print("ctrl", boot("ctrl_mean_R",tr.gate.to_numpy()))
for c in [0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5]:
    m=(tr.ratio<=c).to_numpy(); print(c, m.mean().round(3), "adj",boot("adj",m),"raw",boot("net_R",m))
tr["dec"]=pd.qcut(tr.ratio.rank(method="first"),10,labels=False)
print(tr.groupby("dec")[["ratio","net_R","ctrl_mean_R","adj"]].mean().round(3))
