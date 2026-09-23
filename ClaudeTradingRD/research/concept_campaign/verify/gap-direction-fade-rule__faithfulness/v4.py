import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
exec(open("v2.py").read().split("all_ = ")[0])
o,_=hitm(t,lvl,up,60); a,_=hitm(t,px-dist,up,60,flip=True)
ny=t.tz_convert("America/New_York"); sun=(ny.dayofweek==6)
def ci(x, B=2000):
    x=x[~np.isnan(x)]; r=np.random.default_rng(1); bs=[x[r.integers(0,len(x),len(x))].mean() for _ in range(B)]
    return x.mean(), np.percentile(bs,[2.5,97.5])
# null per event averaged
N=[]
for k in range(5):
    tk=pd.DatetimeIndex(rt[:,k]).tz_localize("UTC"); ok=~tk.isna()
    pk=np.full(len(t),np.nan); pk[ok]=mkt.o[mkt.pos_at_or_after(tk[ok])]
    h,_=hitm(tk,pk+dist,up,60); N.append(h)
N=np.nanmean(np.vstack(N),axis=0)
# Sunday-matched null: draw other Sunday reopens (same decision minute) within +/-120 days
sun_t = t[sun]; rng=np.random.default_rng(cl.rules.SEED)
Ns=np.full(len(t),np.nan)
idx_s=np.flatnonzero(sun)
hs=[]
for k in range(5):
    tk=np.full(len(t), np.datetime64("NaT","ns"), dtype="datetime64[ns]")
    for i in idx_s:
        cand = sun_t[(np.abs((sun_t - t[i]).days) <= 120) & (sun_t != t[i])]
        tk[i]=cand[rng.integers(len(cand))].tz_convert("UTC").tz_localize(None).to_datetime64()
    tk=pd.DatetimeIndex(tk).tz_localize("UTC"); ok=~tk.isna()
    pk=np.full(len(t),np.nan); pk[ok]=mkt.o[mkt.pos_at_or_after(tk[ok])]
    h,_=hitm(tk,pk+dist,up,60); hs.append(h)
Ns=np.nanmean(np.vstack(hs),axis=0)
for nm,s in (("all",np.ones(len(t),bool)),("sunday",sun),("weekday",~sun)):
    m,c=ci(o[s]-N[s]); m2,c2=ci(o[s]-a[s])
    print(f"{nm} n={s.sum()} vs harness-null {m:+.4f} {np.round(c,4)} | vs away-side {m2:+.4f} {np.round(c2,4)}")
m,c=ci(o[sun]-Ns[sun]); print(f"sunday vs Sunday-reopen null {m:+.4f} {np.round(c,4)}  (Sunday null rate {np.nanmean(Ns[sun]):.3f}, harness null {np.nanmean(N[sun]):.3f})")
# weekday halves / blocks
for nm,s in (("wk H1",(~sun)&(t.year<2021)),("wk H2",(~sun)&(t.year>=2021)),("wk 2023+",(~sun)&(t.year>=2023)),("all 2023+",t.year>=2023),("all 2016-2022",t.year<2023)):
    m,c=ci(o[s]-N[s]); print(nm, s.sum(), f"{m:+.4f}", np.round(c,4))
# drop largest gap quartile
rel=np.abs(dist); q=np.quantile(rel,.75)
s=rel<q; m,c=ci(o[s]-N[s]); print("excluding top gap quartile ($)", s.sum(), f"{m:+.4f}", np.round(c,4))
print("sunday share of top-quartile gaps", sun[rel>=q].mean())
Nc = N.copy(); Nc[sun]=Ns[sun]
okc=~np.isnan(Nc)
m,c=ci(o[okc]-Nc[okc]); print("pooled with Sunday-matched null for Sunday rows", okc.sum(), f"{m:+.4f}", np.round(c,4))
for nm,s in (("H1",t.year<2021),("H2",t.year>=2021)):
    s=s&okc; m,c=ci(o[s]-Nc[s]); print(nm, s.sum(), f"{m:+.4f}", np.round(c,4))
bounds=pd.to_datetime(["2016-01-01","2018-08-22","2021-04-12","2023-12-02","2026-08-01"]).tz_localize("UTC")
for i in range(4):
    s=(t>=bounds[i])&(t<bounds[i+1])&okc; m,c=ci(o[s]-Nc[s]); print("B%d"%(i+1), s.sum(), f"{m:+.4f}", np.round(c,4))
