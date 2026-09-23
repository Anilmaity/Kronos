"""Independent re-implementation of failure-to-displace reading a (15m), no harness test code.
Bars: own resample of the raw M1 parquet. Entry: open of first M1 >= bar close. Resolve on M1,
stop first, gap-through fills at open. Control: 5 random M1 minutes on the 15-min grid within +/-30d,
same direction, stop dist, target dist, hold. Day-block bootstrap CI."""
import numpy as np, pandas as pd
m1=pd.read_parquet("/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xau_m1_full.parquet")
m1=m1.set_index(pd.to_datetime(m1["time"],utc=True)).sort_index(); m1=m1[~m1.index.duplicated()]
m1=m1[m1.index>=pd.Timestamp("2016-01-01",tz="UTC")][["open","high","low","close"]].astype(float)
b=m1.resample("15min",label="left",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
b["ct"]=b.index+pd.Timedelta("15min")
h,l,c=b.high.values,b.low.values,b.close.values
ph,pl=np.r_[np.nan,h[:-1]],np.r_[np.nan,l[:-1]]
bear=(h>ph)&(c<ph)&(c>pl)&(l>=pl); bull=(l<pl)&(c>pl)&(c<ph)&(h<=ph)
sel=bear|bull
ev=pd.DataFrame({"dt":b.ct.values[sel],"dir":np.where(bull,1,-1)[sel],"stop":np.where(bull,l,h)[sel],
                 "tgt":np.where(bull,ph,pl)[sel],"close":c[sel]})
print("events",len(ev))
T=m1.index.values.astype("datetime64[ns]").astype(np.int64); O,H,L,C=(m1[k].values for k in ["open","high","low","close"])
N=len(T); HOLD=150*60*10**9; MAXB=400
def resolve(i0,t0,sg,st,tg):
    # vectorised over trades with a window of MAXB bars
    n=len(i0); out=np.full(n,np.nan); reason=np.zeros(n,int)
    for s in range(0,n,20000):
        ii=i0[s:s+20000]; idx=np.minimum(ii[:,None]+np.arange(MAXB)[None,:],N-1)
        valid=(T[idx]<t0[s:s+20000,None]+HOLD)&(ii[:,None]+np.arange(MAXB)[None,:]<N)
        g=sg[s:s+20000,None]; stp=st[s:s+20000,None]; tgt=tg[s:s+20000,None]
        hs=np.where(g>0,L[idx]<=stp,H[idx]>=stp)&valid
        ht=np.where(g>0,H[idx]>=tgt,L[idx]<=tgt)&valid
        fs=np.where(hs.any(1),hs.argmax(1),MAXB); ft=np.where(ht.any(1),ht.argmax(1),MAXB)
        last=valid.sum(1)-1
        px=np.empty(len(ii)); r=np.zeros(len(ii),int)
        stopfirst=(fs<=ft)&(fs<MAXB); tgtfirst=(ft<fs)
        k=np.arange(len(ii))
        # stop fill: gap through -> open
        so=O[idx[k,np.minimum(fs,MAXB-1)]]
        sfill=np.where(g[:,0]>0,np.minimum(so,stp[:,0]),np.maximum(so,stp[:,0]))
        to=O[idx[k,np.minimum(ft,MAXB-1)]]
        tfill=np.where(g[:,0]>0,np.maximum(to,tgt[:,0]),np.minimum(to,tgt[:,0]))
        px=np.where(stopfirst,sfill,np.where(tgtfirst,tfill,C[idx[k,np.maximum(last,0)]]))
        r=np.where(stopfirst,1,np.where(tgtfirst,2,3))
        out[s:s+20000]=px; reason[s:s+20000]=r
    return out,reason
t0=ev.dt.values.astype("datetime64[ns]").astype(np.int64)
i0=np.searchsorted(T,t0); ok=i0<N
entry=O[np.minimum(i0,N-1)]; sg=ev.dir.values
risk=sg*(entry-ev.stop.values); td=sg*(ev.tgt.values-entry)
ok&=(risk>0)&(td>0)
ev=ev[ok].reset_index(drop=True); i0,t0,entry,sg,risk,td=i0[ok],t0[ok],entry[ok],sg[ok],risk[ok],td[ok]
px,rs=resolve(i0,t0,sg,ev.stop.values,ev.tgt.values)
R=sg*(px-entry)/risk
print("n",len(R),"real avgR gross",R.mean(),"win",(R>0).mean())
rng=np.random.default_rng(7); REPS=5
grid=T[(T//60_000_000_000)%15==0]
cR=np.zeros((len(R),REPS))
for k in range(REPS):
    off=rng.uniform(-30,30,len(R))*86400e9
    ct=np.searchsorted(grid,(t0+off).astype(np.int64)); ct=np.clip(ct,0,len(grid)-1)
    ctime=grid[ct]; ci=np.searchsorted(T,ctime); ce=O[ci]
    cst=ce-sg*risk; ctg=ce+sg*td
    cp,_=resolve(ci,ctime,sg,cst,ctg); cR[:,k]=sg*(cp-ce)/risk
cm=cR.mean(1); d=R-cm
day=pd.DatetimeIndex(pd.to_datetime(t0,utc=True)).tz_convert("America/New_York")
dayc=pd.factorize((day+pd.Timedelta("6h")).date)[0]
def ci(mask,nb=1000):
    dd=d[mask]; dc=pd.factorize(dayc[mask])[0]; nd=dc.max()+1
    s=np.bincount(dc,dd,nd); cnt=np.bincount(dc,None,nd); bs=[]
    r=np.random.default_rng(1)
    for _ in range(nb):
        w=np.bincount(r.integers(0,nd,nd),minlength=nd); bs.append((w*s).sum()/(w*cnt).sum())
    return dd.mean(),np.percentile(bs,2.5),np.percentile(bs,97.5),mask.sum()
yr=pd.DatetimeIndex(pd.to_datetime(t0,utc=True)).year
allm=np.ones(len(d),bool)
print("ALL diff/CI",ci(allm)); print("H1",ci(yr<2021)); print("H2",ci(yr>=2021))
dstop=np.abs(ev.close.values-ev.stop.values)/ev.close.values   # decision-time knowable
for thr in [0.00005,0.0001,0.0002,0.0003]:
    m=dstop>=thr; print(f"stop from close >= {thr*1e4:.1f}bp",ci(m),"H1",d[m&(yr<2021)].mean(),"H2",d[m&(yr>=2021)].mean())
for q in [0.999,0.995]:
    m=np.abs(d)<np.quantile(np.abs(d),q); print("trim",q,ci(m))
m=risk>=0.3; print("risk>=0.30$",ci(m))
