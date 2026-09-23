import sys; sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import numpy as np, pandas as pd, concept_lab as cl
NY="America/New_York"; rng=np.random.default_rng(7)
ev=pd.read_pickle("ev_indep.pkl"); m1=cl.load_m1()
mny=m1.index.tz_convert(NY); td=(mny+pd.Timedelta(hours=6)).date
d=pd.DataFrame({"h":m1.high.to_numpy(),"l":m1.low.to_numpy(),"td":td}).groupby("td").agg(h=("h","max"),l=("l","min"),n=("h","size"))
d=d[d.n>=600]; rngd=(d.h-d.l); atr=rngd.rolling(20).mean().shift(1)
ev["day"]=ev.t.dt.tz_convert(NY).dt.date
ev["atr"]=ev.day.map(atr); ev=ev.dropna(subset=["atr"])
ev["dn"]=ev.dist/ev.atr
days=np.array(sorted(ev.day.unique()))
def boot(fun, B=2000):
    # day-block (iid over days) bootstrap of a statistic computed from per-day frames
    gi={dd:np.flatnonzero(ev.day.to_numpy()==dd) for dd in days}
    out=[]
    for _ in range(B):
        s=rng.choice(days,len(days)); idx=np.concatenate([gi[x] for x in s]); out.append(fun(ev.iloc[idx]))
    return np.percentile(out,[2.5,97.5])
# B: guarded vs unguarded untaken swing targets, stratified by side x dist/ATR bins (weights = guarded counts)
bins=np.r_[0,np.quantile(ev.dn,np.linspace(0,1,21)[1:-1]),np.inf]
ev["bin"]=np.digitize(ev.dn,bins)
def strat(f):
    gg=f.groupby(["side","bin","guarded"]).hit.agg(["mean","size"]).unstack("guarded")
    gg=gg.dropna()
    w=gg[("size",True)]; return float(((gg[("mean",True)]-gg[("mean",False)])*w).sum()/w.sum())
est=strat(ev); print("B guarded-unguarded stratified by dist/ATR (20 bins) x side:",est, boot(strat,500))
for nm,sub in (("H1",ev[ev.t<"2021-01-01"]),("H2",ev[ev.t>="2021-01-01"])): print("  ",nm,strat(sub))
print("  coverage: guarded rows in strata", ev.guarded.sum())
# finer: 40 bins
bins2=np.r_[0,np.quantile(ev.dn,np.linspace(0,1,41)[1:-1]),np.inf]; ev["bin"]=np.digitize(ev.dn,bins2)
print("B40:",strat(ev), boot(strat,500))
# also control age of target (older untaken swing) and nkeep
ev["bin"]=np.digitize(ev.dn,bins)*10+np.minimum(ev.age//30,9)
print("B dist x age:",strat(ev), boot(strat,500))
ev.to_pickle("ev_indep_atr.pkl")
