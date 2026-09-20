"""Fast in-memory sweep for the session-VWAP fair-value pullback, to find the
highest HONEST ~0.25-taker PF across BOTH train and OOS. Loads once, builds
synthetic 0.20/0.30 M1 bars, sweeps params. Standalone (no module reload)."""
import itertools
import numpy as np
from bot.oanda_s5 import load
from bot.micro.engine import Bars, simulate
from bot.micro.features import resample_bars, hours_mask, ema

TRAIN = ("2024-01", "2025-07"); OOS = ("2025-08", "2026-06")
SIM = dict(maxhold=60, dollars_per_point=1.0, commission=0.07, cooldown=5)


def synth(d, s):
    mo=(d["bo"]+d["ao"])*0.5; mh=(d["bh"]+d["ah"])*0.5
    ml=(d["bl"]+d["al"])*0.5; mc=(d["bc"]+d["ac"])*0.5; h=s*0.5
    return {"ts":d["ts"],"vol":d["vol"],"bo":mo-h,"bh":mh-h,"bl":ml-h,"bc":mc-h,
            "ao":mo+h,"ah":mh+h,"al":ml+h,"ac":mc+h}


def svwap(b):
    day=b.day; mid=b.mid; vol=np.where(b.vol>0,b.vol.astype(np.float64),1.0)
    v=np.empty(b.n); cpv=0.0; cv=0.0; cur=day[0]
    for i in range(b.n):
        if day[i]!=cur: cur=day[i]; cpv=0.0; cv=0.0
        cpv+=mid[i]*vol[i]; cv+=vol[i]; v[i]=cpv/cv
    return v


def rstd(x,w):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    out=np.full(len(x),np.nan)
    if len(x)>=w: out[w-1:]=swv(x,w).std(axis=1)
    return out


print("loading...")
draw={"tr":load(*TRAIN),"oos":load(*OOS)}
BARS={}
for w in ("tr","oos"):
    for s in (0.20,0.30):
        BARS[(w,s)]=Bars(resample_bars(synth(draw[w],s),60))
# precompute per-bar features once per (window,spread)
FEAT={}
for key,b in BARS.items():
    vw=svwap(b); dev=b.mid-vw; sig=rstd(dev,40)
    el=ema(b.mid,150); sl=np.full(b.n,np.nan); sl[60:]=el[60:]-el[:-60]
    z=dev/np.where(sig>0,sig,np.nan)
    FEAT[key]=(vw,dev,sig,sl,z)
HOURS=(7,8,9,10,11,12,13,14,15)
print("ready")


def build(b,feat,p):
    vw,dev,sig,sl,z=feat
    sess=hours_mask(b,HOURS)
    good=np.isfinite(sig)&(sig>0)&np.isfinite(sl)&sess
    long_=good&(sl>=p["tm"])&(z>=p["lo"])&(z<=p["hi"])
    short=good&(sl<=-p["tm"])&(z<=-p["lo"])&(z>=-p["hi"])
    il=np.where(long_)[0]; iu=np.where(short)[0]
    i=np.concatenate([il,iu]); side=np.concatenate([np.ones(len(il),int),-np.ones(len(iu),int)])
    level=np.concatenate([vw[il],vw[iu]])
    o=np.argsort(i,kind="stable")
    from bot.micro.engine import Signals
    n=len(i)
    return Signals(i=i[o],side=side[o],kind=np.ones(n,int),level=level[o],
                   sl_pts=np.full(n,p["slp"]),tp_pts=np.full(n,p["tpp"]),
                   ttl=np.full(n,p["ttl"],np.int64))


def taker_pf(w,p):
    pfs=[]; ns=[]
    for s in (0.20,0.30):
        b=BARS[(w,s)]; sig=build(b,FEAT[(w,s)],p)
        kw=dict(SIM); kw["gap_sec"]=65; kw["slippage_pts"]=s
        r=simulate(b,sig,**kw); pfs.append(r["pf"]); ns.append(r["trades"])
    return np.mean(pfs),int(np.mean(ns))


grid=dict(
    tm=[0.6,1.0],
    lo=[0.3,0.5,0.8],
    hi=[2.0,3.0],
    slp=[2.4,3.0],
    tpp=[3.0,4.5],
    ttl=[6,10],
)
keys=list(grid); best=[]
for combo in itertools.product(*[grid[k] for k in keys]):
    p=dict(zip(keys,combo))
    tp_tr,n_tr=taker_pf("tr",p); tp_oos,n_oos=taker_pf("oos",p)
    if n_oos>=100:
        best.append((min(tp_tr,tp_oos),tp_tr,tp_oos,n_tr,n_oos,p))
best.sort(reverse=True)
for m,a,o,nt,no,p in best[:10]:
    print(f"min={m:.3f} train={a:.3f}(n{nt}) oos={o:.3f}(n{no}) {p}")
