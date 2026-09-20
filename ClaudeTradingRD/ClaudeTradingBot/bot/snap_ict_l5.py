"""L5 LOCKED — high-WR fade + session + daily ICT bias + FVG filter + bounded stop with a
HARD CAP (no single trade can run past the cap). Walk-forward by year, then compared over
the real account's traded window (Jun 21-24 2026) and full history.

Taker, spread 0.20pt, $10/pt @0.10 lot. Stop = min(1.5*overshoot, MAX_STOP_PT).
MAX_STOP_PT chosen as a RISK level (~0.6% of $5k at 3pt), not optimized; 5/8 shown for context.
"""
import csv, numpy as np, os
CSV=os.path.join(os.path.dirname(__file__),"..","reports","xau_m5_3y.csv")
LB=2;K=1.0;W=200;SPREAD=0.20;USD=10.0;FRACT=2
t=[];c=[];h=[];l=[]
for r in csv.DictReader(open(CSV,encoding="utf-8")):
    t.append(r["time"]);c.append(float(r["c"]));h.append(float(r["h"]));l.append(float(r["l"]))
c=np.array(c);h=np.array(h);l=np.array(l);n=len(c);hour=np.array([int(x[11:13]) for x in t])
mv=np.full(n,np.nan);mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0);cs=np.cumsum(mv2);cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
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
def has_fvg(i,up): return (l[i]>h[i-2]) if up else (h[i]<l[i-2])

def backtest(MAX_STOP, d0=None, d1=None):
    out=[];i=W+1
    while i<n-2:
        if d0 and not(d0<=t[i][:10]<=d1): i+=1;continue
        if not(np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and abs(mv[i])>=K*sd[i]): i+=1;continue
        if not(3<=hour[i]<=9): i+=1;continue
        up=mv[i]>0;side=-1 if up else 1;ov=abs(mv[i])
        if bias[i]==0 or np.sign(side)!=bias[i]: i+=1;continue
        if not has_fvg(i,up): i+=1;continue
        entry=c[i];stopdist=min(1.5*ov,MAX_STOP)
        tp=entry-0.5*ov if up else entry+0.5*ov
        st=entry+stopdist if up else entry-stopdist
        ex=None
        for j in range(i+1,min(i+1+120,n)):
            if up:
                if h[j]>=st: ex=st;break
                if l[j]<=tp: ex=tp;break
            else:
                if l[j]<=st: ex=st;break
                if h[j]>=tp: ex=tp;break
        if ex is None: ex=c[min(i+120,n-1)]
        out.append(((ex-entry)*side-SPREAD, t[i]));i=j+1
    return out

def stat(rows,a,b):
    p=np.array([r[0] for r in rows if a<=r[1][:10]<=b])
    if len(p)<1: return None
    gp=p[p>0].sum();gl=-p[p<0].sum()
    return len(p),100*(p>0).mean(),p.sum()*USD,(gp/gl if gl>0 else float('inf')),p.min()*USD

if __name__=="__main__":
    print("=== L5 hard-stop-cap sweep — walk-forward by year (0.10 lot) ===")
    for cap in (3.0,5.0,8.0):
        tr=backtest(cap)
        print(f"\n  MAX_STOP={cap}pt:")
        for y in ("2023","2024","2025","2026"):
            s=stat(tr,f"{y}-01-01",f"{y}-12-31")
            if s: print(f"    {y}: n={s[0]:4d} WR={s[1]:4.0f}% net=${s[2]:>+7,.0f} PF={s[3]:.2f} worst=${s[4]:>+5,.0f}")
    print("\n=== LOCKED cap=3pt — comparison vs the real account ===")
    tr=backtest(3.0)
    for lab,a,b in [("Order window Jun21-24","2026-06-21","2026-06-24"),
                    ("Last week Jun18-24","2026-06-18","2026-06-24"),
                    ("Full history 2023-26","2023-01-01","2026-12-31")]:
        s=stat(tr,a,b)
        print(f"  {lab:24s} " + (f"n={s[0]:4d} WR={s[1]:.0f}% net=${s[2]:+,.0f} PF={s[3]:.2f} worst=${s[4]:+,.0f}" if s else "no trades"))
    print("  Real account Jun21-24    n=  67 WR=92.5% net=+$452 PF=20.84  (no stop, all hours, lucky 2-day burst)")
