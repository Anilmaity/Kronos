"""Stack the user's filters on the high-WR fade and watch the damage, over RECENT data
(2026-01-01..06-24). Cumulative layers; taker spread 0.20pt; $10/pt @0.10 lot.

Layers:
  L1 raw high-WR fade (all hours, TP0.5/SL10 wide)         <- 90% WR, loses
  L2 + session filter (03-09 UTC)
  L3 + daily ICT bias (with-trend only)
  L4 + FVG filter (overshoot left an imbalance to revert into)
  L5 + REAL bounded stop (target 0.5x move / stop 1.5x move) <- the risk parameter
Also shown: L5 + AVERAGING (add a 2nd unit at -1x move, no extra stop) to demonstrate
that averaging RAISES win rate but FATTENS the worst trade.
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.0;W=200;SPREAD=0.20;USD=10.0;FRACT=2
D0,D1="2026-01-01","2026-06-24"
t=[];c=[];h=[];l=[]
for r in csv.DictReader(open(CSV,encoding="utf-8")):
    t.append(r["time"]);c.append(float(r["c"]));h.append(float(r["h"]));l.append(float(r["l"]))
c=np.array(c);h=np.array(h);l=np.array(l);n=len(c)
hour=np.array([int(x[11:13]) for x in t])
mv=np.full(n,np.nan);mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0);cs=np.cumsum(mv2);cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
# daily ICT bias
keys=[];H=[];Lo=[];C=[];m5b=np.empty(n,int);idx={}
for i in range(n):
    d=t[i][:10]
    if d not in idx: idx[d]=len(keys);keys.append(d);H.append(h[i]);Lo.append(l[i]);C.append(c[i])
    else: b=idx[d];H[b]=max(H[b],h[i]);Lo[b]=min(Lo[b],l[i]);C[b]=c[i]
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
# FVG: up-overshoot leaves bullish gap (l[i]>h[i-2]); down leaves bearish (h[i]<l[i-2])
def has_fvg(i,up):
    return (l[i]>h[i-2]) if up else (h[i]<l[i-2])

def sim(session=False,usebias=False,usefvg=False,bounded=False,averaging=False):
    TPw,SLw=0.5,10.0
    out=[];i=W+1
    while i<n-2:
        if not(D0<=t[i][:10]<=D1): i+=1;continue
        if not(np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and abs(mv[i])>=K*sd[i]): i+=1;continue
        if session and not(3<=hour[i]<=9): i+=1;continue
        up=mv[i]>0;side=-1 if up else 1;ov=abs(mv[i])
        if usebias and (bias[i]==0 or np.sign(side)!=bias[i]): i+=1;continue
        if usefvg and not has_fvg(i,up): i+=1;continue
        e0=c[i]; entry=e0
        if bounded:
            tp=entry-0.5*ov if up else entry+0.5*ov
            st=entry+1.5*ov if up else entry-1.5*ov
        else:
            tp=entry-TPw if up else entry+TPw
            st=entry+SLw if up else entry-SLw
        add_done=False; size=1.0; cost=SPREAD
        ex=None
        for j in range(i+1,min(i+1+120,n)):
            if averaging and not add_done:   # add a 2nd unit if price goes 1x move against
                adverse = (h[j]>=e0+ov) if up else (l[j]<=e0-ov)
                if adverse:
                    e1 = e0+ov if up else e0-ov           # 2nd entry, 1x move worse
                    entry = (e0+e1)/2.0                    # averaged entry
                    size=2.0; cost+=SPREAD; add_done=True
                    tp = entry-0.5*ov if up else entry+0.5*ov
                    st = e1+1.5*ov   if up else e1-1.5*ov  # stop beyond the 2nd entry
            if up:
                if h[j]>=st: ex=st;break
                if l[j]<=tp: ex=tp;break
            else:
                if l[j]<=st: ex=st;break
                if h[j]>=tp: ex=tp;break
        if ex is None: ex=c[min(i+120,n-1)]
        out.append(((ex-entry)*side*size - cost)); i=j+1
    return np.array(out)

def show(name,p):
    if len(p)<5: print(f"  {name:38s} n={len(p)} (too few)");return
    wr=100*(p>0).mean();net=p.sum()*USD;worst=p.min()*USD
    aw=p[p>0].mean()*USD if (p>0).any() else 0
    print(f"  {name:38s} n={len(p):4d}  WR={wr:5.1f}%  net=${net:>+8,.0f}  worst=${worst:>+6,.0f}  erase={abs(worst)/aw if aw>0 else 0:4.0f}x")

print(f"=== Stacking filters on the high-WR fade, RECENT window {D0}..{D1} ===")
show("L1 raw (all hrs, wide stop)",     sim())
show("L2 +session 03-09",               sim(session=True))
show("L3 +daily ICT bias",              sim(session=True,usebias=True))
show("L4 +FVG filter",                  sim(session=True,usebias=True,usefvg=True))
show("L5 +REAL bounded stop",           sim(session=True,usebias=True,usefvg=True,bounded=True))
show("L5+AVERAGING (martingale add)",   sim(session=True,usebias=True,usefvg=True,bounded=False,averaging=True))
print("\n(Watch: filters cut trades & losses; the BOUNDED STOP is what stops the bleed —")
print(" and it lowers WR. AVERAGING lifts WR but look at the worst trade.)")
