import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
f = pd.read_pickle("f.pkl"); t = pd.DatetimeIndex(f.decision_time); up=f.up.to_numpy(); lvl=f.prev_close.to_numpy(); px=f.px.to_numpy()
dist = lvl-px; mkt=cl.get_market()
rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=30)
def hitm(tt, level, upm, H, flip=False):
    out = np.full(len(tt), np.nan); mins=np.full(len(tt), np.nan)
    for m, side in ((upm,"below"),(~upm,"above")):
        if flip: side = {"below":"above","above":"below"}[side]
        m = m & ~pd.isna(tt)
        if m.any():
            r = cl.touch(tt[m], level[m], side, horizon_bars=H); out[m]=r["hit"].to_numpy(); mins[m]=r["minutes"].to_numpy()
    return out, mins
def nullrate(H, sel):
    rs=[]
    for k in range(5):
        tk = pd.DatetimeIndex(rt[:,k]).tz_localize("UTC"); ok=~tk.isna()
        pk=np.full(len(t),np.nan); pk[ok]=mkt.o[mkt.pos_at_or_after(tk[ok])]
        h,_=hitm(tk, pk+dist, up, H); rs.append(h[sel])
    return np.nanmean(np.concatenate(rs))
def boot(a,b,day, B=1000):
    # paired by event diff a - b, iid bootstrap
    dlt = a-b; rng=np.random.default_rng(0); n=len(dlt)
    bs=[np.nanmean(dlt[rng.integers(0,n,n)]) for _ in range(B)]; return np.nanmean(dlt), np.percentile(bs,[2.5,97.5])
all_ = np.ones(len(t),bool)
for H in (15,30,60,120,240):
    o,mins=hitm(t,lvl,up,H); n=nullrate(H,all_); a,_=hitm(t,px-dist,up,H,flip=True)
    print(f"H={H}: obs {np.nanmean(o):.4f} null {n:.4f} diff {np.nanmean(o)-n:+.4f} | awayside {np.nanmean(a):.4f} fill-away {np.nanmean(o)-np.nanmean(a):+.4f}")
o,mins=hitm(t,lvl,up,60)
print("share of hits at minute 0:", np.mean(mins[o==1]==0), " <=2:", np.mean(mins[o==1]<=2))
# ATR scale
d=cl.bars("1D"); rng_=(d.high-d.low).rolling(14).mean(); ct=pd.DatetimeIndex(d.close_time)
idx=np.searchsorted(ct.asi8, t.asi8, side="right")-1; atr=rng_.to_numpy()[idx]
rel=np.abs(dist)/atr; print("rel gap quantiles", np.quantile(rel,[.25,.5,.75,.9]))
qs=np.quantile(rel,[0,.25,.5,.75,1.0001])
for i in range(4):
    s=(rel>=qs[i])&(rel<qs[i+1])
    print(f"gap quartile {i+1} rel [{qs[i]:.3f},{qs[i+1]:.3f}) n={s.sum()} obs {np.nanmean(o[s]):.3f} null {nullrate(60,s):.3f} diff {np.nanmean(o[s])-nullrate(60,s):+.3f}")
# excluding immediate (<=2 min) hits
o2=o.copy(); o2[(o==1)&(mins<=2)]=0
print("obs if hits within 2 min are dropped (counted miss):", np.nanmean(o2))
# weekday vs Sunday
ny=t.tz_convert("America/New_York"); sun = ny.dayofweek==6
for nm,s in (("sunday",sun),("weekday",~sun)):
    print(nm, s.sum(), f"obs {np.nanmean(o[s]):.3f} null {nullrate(60,s):.3f}")
# by year
for y in range(2016,2027):
    s=t.year==y
    if s.sum(): print(y, s.sum(), f"diff {np.nanmean(o[s])-nullrate(60,s):+.3f}")
# first-minute-late (data starting at 18:04/18:05) vs 18:01
late = ny.minute>=3
for nm,s in (("decide 18:01-02",~late),("decide 18:04+",late)):
    print(nm, s.sum(), f"diff {np.nanmean(o[s])-nullrate(60,s):+.3f}")
