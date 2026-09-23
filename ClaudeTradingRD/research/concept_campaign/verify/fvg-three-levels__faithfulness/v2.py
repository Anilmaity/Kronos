import numpy as np, pandas as pd
o=pd.read_pickle("races.pkl"); t=o["t"]; ev=pd.read_pickle("ev.pkl")
day=(t.tz_convert("America/New_York")+pd.Timedelta(hours=6)).normalize()
codes,uniq=pd.factorize(day)
rng=np.random.default_rng(1)
def boot(x):
    m=~np.isnan(x); x=x[m]; c=codes[m]
    s=np.bincount(c,weights=x,minlength=len(uniq)); n=np.bincount(c,minlength=len(uniq))
    bs=[]
    for _ in range(1000):
        w=np.bincount(rng.integers(0,len(uniq),len(uniq)),minlength=len(uniq))
        bs.append((w*s).sum()/(w*n).sum())
    return x.mean(), np.percentile(bs,[2.5,97.5])
def rep(lbl,x): m,ci=boot(x); print(f"{lbl:40s} {m*100:+.2f}pp [{ci[0]*100:+.2f},{ci[1]*100:+.2f}]")
Ho,Io=o["Ho"],o["Io"]
print("obs hit %.4f inv %.4f"%(np.nanmean(Ho),np.nanmean(Io)))
for nm in ("base","tod30"):
    print(nm,"null hit %.4f inv %.4f"%(np.nanmean(o[nm+"_H"]),np.nanmean(o[nm+"_I"])))
    rep(nm+" hit diff",Ho-o[nm+"_H"])
    rep(nm+" inv diff",Io-o[nm+"_I"])
    # share of resolved races that are target-first
    ro=Ho/(Ho+Io); rn=o[nm+"_H"]/(o[nm+"_H"]+o[nm+"_I"])
    print("  resolved target share obs %.4f null %.4f"%(np.nansum(Ho)/(np.nansum(Ho)+np.nansum(Io)), np.nanmean(o[nm+"_H"])/(np.nanmean(o[nm+"_H"])+np.nanmean(o[nm+"_I"]))))
    rep(nm+" (hit - inv) diff", (Ho-Io)-(o[nm+"_H"]-o[nm+"_I"]))
    # blocks & halves
    x=Ho-o[nm+"_H"]
    for y in range(2016,2027):
        s=(t.year==y); print(f"   {y}: n={s.sum()} {np.nanmean(x[s])*100:+.2f}pp", end="")
    print()
# distance structure
d=ev.direction.to_numpy(); up=d*(ev.leg_extreme-ev.touch_close); dn=d*(ev.touch_close-ev.far_edge)
r=(up/dn).to_numpy(); q=pd.qcut(r,4,labels=False)
for k in range(4):
    s=q==k; print("ratio q",k,"med %.2f"%np.median(r[s]), "diff base %+.2f tod %+.2f"%(np.nanmean(Ho[s]-o['base_H'][s])*100,np.nanmean(Ho[s]-o['tod30_H'][s])*100))
# NY hour profile
h=t.tz_convert("America/New_York").hour
print(pd.Series(Ho-o['base_H']).groupby(h).agg(['mean','size']).round(3).T.to_string())
