"""Backtest the late-Asia/London snap-fade with the user's REAL tight spread.
Units: 100 pips = 1 pt; spread = 20 pips = 0.20 pt = $0.20 on XAU.  half-spread = 0.10 pt.

Two honest execution models, same geometry, IS(2023-24) vs OOS(2025-26, judged once):

  TAKER : market entry the instant the overshoot prints, cross the spread in AND out.
          No adverse selection (you take liquidity), but you pay the full spread round-trip.
  MAKER : passive limit entry -> fills only on CONTINUATION (adverse selection baked in),
          earn half-spread on entry; exit at target = limit (earn half-spread), exit at
          stop/time = market (pay half-spread).
"""
import csv, numpy as np

CSV="reports/xau_m5_3y.csv"
LB=2; K=1.2; W=200
OFFSET=0.25; FILL_WIN=3; TARGET_F=0.5; STOP_F=1.5; TIME=6
SPREAD=0.20; HALF=SPREAD/2; COMMISSION=0.0   # set COMMISSION if the account charges per-side $ in pt-equiv

def load(p):
    t,c,h,l=[],[],[],[]
    with open(p,encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(r["time"]); c.append(float(r["c"])); h.append(float(r["h"])); l.append(float(r["l"]))
    hour=np.array([int(x[11:13]) for x in t]); yr=np.array([int(x[:4]) for x in t])
    return np.array(c),np.array(h),np.array(l),hour,yr

c,h,l,hour,yr=load(CSV)
n=len(c); ret=np.diff(c,prepend=c[0])
mv=np.full(n,np.nan); mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0); cs=np.cumsum(mv2); cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
ar=np.abs(ret); arc=np.cumsum(ar); rv=np.full(n,np.nan)
for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
vmed=np.nanmedian(rv)
WIN=lambda hh:(hh>=3)&(hh<=9); CTRL=lambda hh:(hh>=0)&(hh<=2)

def cand(i,win_fn):
    return (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and win_fn(hour[i])
            and np.isfinite(rv[i]) and rv[i]<vmed and abs(mv[i])>=K*sd[i])

def taker(win_fn):
    out=[]; i=W+1
    while i<n-2:
        if not cand(i,win_fn): i+=1; continue
        up=mv[i]>0; side=-1 if up else 1
        entry=c[i]; ov=abs(mv[i])
        target=entry-TARGET_F*ov if up else entry+TARGET_F*ov
        stop  =entry+STOP_F*ov   if up else entry-STOP_F*ov
        ex=None
        for j in range(i+1,min(i+1+TIME,n)):
            if up:
                if h[j]>=stop: ex=stop; break
                if l[j]<=target: ex=target; break
            else:
                if l[j]<=stop: ex=stop; break
                if h[j]>=target: ex=target; break
        if ex is None: ex=c[min(i+TIME,n-1)]
        pnl=(ex-entry)*side - SPREAD - 2*COMMISSION   # cross in and out
        out.append((pnl,yr[i])); i=j+1
    return out

def maker(win_fn):
    out=[]; i=W+1
    while i<n-2:
        if not cand(i,win_fn): i+=1; continue
        up=mv[i]>0; side=-1 if up else 1
        L=c[i]+(OFFSET*sd[i] if up else -OFFSET*sd[i])
        fj=None
        for j in range(i+1,min(i+1+FILL_WIN,n)):
            if up and h[j]>=L: fj=j; break
            if (not up) and l[j]<=L: fj=j; break
        if fj is None: i+=1; continue
        entry=L; ov=abs(mv[i])
        target=entry-TARGET_F*ov if up else entry+TARGET_F*ov
        stop  =entry+STOP_F*ov   if up else entry-STOP_F*ov
        ex=None; maker_exit=False
        for j in range(fj+1,min(fj+1+TIME,n)):
            if up:
                if h[j]>=stop: ex=stop; break
                if l[j]<=target: ex=target; maker_exit=True; break
            else:
                if l[j]<=stop: ex=stop; break
                if h[j]>=target: ex=target; maker_exit=True; break
        if ex is None: ex=c[min(fj+TIME,n-1)]
        spread_adj = +HALF + (HALF if maker_exit else -HALF)   # earn on entry; earn/pay on exit
        pnl=(ex-entry)*side + spread_adj - 2*COMMISSION
        out.append((pnl,yr[i])); i=j+1
    return out

def stat(rows,lo,hi):
    p=np.array([r[0] for r in rows if lo<=r[1]<=hi])
    if len(p)<20: return None
    gp=p[p>0].sum(); gl=-p[p<0].sum(); pf=gp/gl if gl>0 else np.inf
    return len(p),100*(p>0).mean(),p.mean(),p.sum(),pf,np.sort(p)[:3]

print(f"SPREAD={SPREAD}pt (20 pips) half={HALF} commission={COMMISSION}pt/side")
print(f"geom LB={LB} K={K} offset={OFFSET}s fillwin={FILL_WIN} tgt={TARGET_F}xmv stop={STOP_F}xmv time={TIME}\n")
for label,win in (("WINDOW 03-09 UTC",WIN),("CONTROL 00-02 UTC",CTRL)):
    print(f"=== {label} ===")
    for nm,fnsim in (("TAKER",taker),("MAKER (adverse-sel)",maker)):
        rows=fnsim(win)
        si=stat(rows,2023,2024); so=stat(rows,2025,2026)
        if not si or not so: print(f"  {nm:20s} insufficient"); continue
        print(f"  {nm:20s} IS: n={si[0]:4d} WR={si[1]:.1f}% exp={si[2]:+.3f} PF={si[4]:.2f}"
              f"  |  OOS: n={so[0]:4d} WR={so[1]:.1f}% exp={so[2]:+.3f} PF={so[4]:.2f} net={so[3]:+.1f}pt worst3={so[5].round(1)}")
    print()
print("DONE")
