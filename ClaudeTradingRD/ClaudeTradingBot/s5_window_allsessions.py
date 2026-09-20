"""Over the REAL order window (2026-06-21 22:00 -> 06-24 00:05), ALL SESSIONS (all hours),
filters opened progressively to raise trade count. Maker fade, daily bias, proportional
stop. Reports trades, WR, net$, and MAX LOSING TRADE vs the real account.
Real account that window: 67 trades, 92.5% WR, +$452.44, max losing trade -$13.80.
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.0;W=200;OFFSET=0.25;FILL_WIN=3;TARGET_F=0.5;STOP_F=1.5;TIME=6
SPREAD=0.20;HALF=0.10;USD=10.0;FRACT=2;LOWTEMPO_WIN=5760
P0,P1="2026-06-21 22:00:00","2026-06-24 00:05:00"
t=[];c=[];h=[];l=[]
for r in csv.DictReader(open(CSV,encoding="utf-8")):
    t.append(r["time"]);c.append(float(r["c"]));h.append(float(r["h"]));l.append(float(r["l"]))
c=np.array(c);h=np.array(h);l=np.array(l);n=len(c);ret=np.diff(c,prepend=c[0]);hour=np.array([int(x[11:13]) for x in t])
mv=np.full(n,np.nan);mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0);cs=np.cumsum(mv2);cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
ar=np.abs(ret);arc=np.cumsum(ar);rv=np.full(n,np.nan)
for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
rvf=np.where(np.isfinite(rv),rv,0.0);rvc=np.cumsum(rvf);fc=np.cumsum(np.isfinite(rv).astype(float))
thr=np.full(n,np.nan)
for i in range(LOWTEMPO_WIN,n):
    k=fc[i]-fc[i-LOWTEMPO_WIN]
    if k>500: thr[i]=(rvc[i]-rvc[i-LOWTEMPO_WIN])/k
keys=[];H=[];Lo=[];C=[];m5b=np.empty(n,int);idx={}
for i in range(n):
    d=t[i][:10]
    if d not in idx: idx[d]=len(keys);keys.append(d);H.append(h[i]);Lo.append(l[i]);C.append(c[i])
    else: bb=idx[d];H[bb]=max(H[bb],h[i]);Lo[bb]=min(Lo[bb],l[i]);C[bb]=c[i]
    m5b[i]=idx[d]
H=np.array(H);Lo=np.array(Lo);C=np.array(C);M=len(keys);cSH={};cSL={}
for k in range(FRACT,M-FRACT):
    if H[k]==H[k-FRACT:k+FRACT+1].max() and H[k]>H[k-1] and H[k]>H[k+1]: cSH[k+FRACT]=H[k]
    if Lo[k]==Lo[k-FRACT:k+FRACT+1].min() and Lo[k]<Lo[k-1] and Lo[k]<Lo[k+1]: cSL[k+FRACT]=Lo[k]
bd=np.zeros(M,int);sh=sl=None;b=0
for k in range(M):
    if k in cSH: sh=cSH[k]
    if k in cSL: sl=cSL[k]
    if sh is not None and C[k]>sh: b=+1
    elif sl is not None and C[k]<sl: b=-1
    bd[k]=b
bias=np.array([bd[m5b[i]-1] if m5b[i]-1>=0 else 0 for i in range(n)])

def run(lowtempo=True,usebias=True):
    out=[];i=W+1
    while i<n-2:
        if not(P0<=t[i]<=P1): i+=1;continue
        if not(np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and abs(mv[i])>=K*sd[i]): i+=1;continue
        if lowtempo and not(np.isfinite(rv[i]) and np.isfinite(thr[i]) and rv[i]<thr[i]): i+=1;continue
        up=mv[i]>0;side=-1 if up else 1;ov=abs(mv[i])
        if usebias and (bias[i]==0 or np.sign(side)!=bias[i]): i+=1;continue
        L=c[i]+(OFFSET*sd[i] if up else -OFFSET*sd[i]);fj=None
        for j in range(i+1,min(i+1+FILL_WIN,n)):
            if up and h[j]>=L: fj=j;break
            if (not up) and l[j]<=L: fj=j;break
        if fj is None: i+=1;continue
        entry=L;target=entry-TARGET_F*ov if up else entry+TARGET_F*ov;stop=entry+STOP_F*ov if up else entry-STOP_F*ov
        ex=None;mk=False
        for j in range(fj+1,min(fj+1+TIME,n)):
            if up:
                if h[j]>=stop: ex=stop;break
                if l[j]<=target: ex=target;mk=True;break
            else:
                if l[j]<=stop: ex=stop;break
                if h[j]>=target: ex=target;mk=True;break
        if ex is None: ex=c[min(fj+TIME,n-1)]
        out.append((ex-entry)*side+HALF+(HALF if mk else -HALF));i=j+1
    return np.array(out)

print(f"=== Order window {P0} -> {P1}, ALL SESSIONS (all hours) ===")
print(f"{'config':40s} {'trades':>6} {'WR':>6} {'net$':>8} {'maxLoss$':>9}")
for name,kw in [("full filters (low-tempo+bias)",dict()),
                ("all hours, NO low-tempo",dict(lowtempo=False)),
                ("all hours, NO low-tempo, NO bias",dict(lowtempo=False,usebias=False))]:
    p=run(**kw)
    if len(p)<1: print(f"{name:40s} {0:>6}      --");continue
    print(f"{name:40s} {len(p):>6} {100*(p>0).mean():>5.0f}% {p.sum()*USD:>+8.0f} {p.min()*USD:>+9.0f}")
print(f"{'REAL ACCOUNT (no stop, all hours)':40s} {67:>6} {'92.5%':>6} {'+452':>8} {'-13.80':>9}")
print("DONE")
