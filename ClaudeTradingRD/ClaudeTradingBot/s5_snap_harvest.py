"""Sharp test of the user's refined thesis: harvest the SHORT reversion snap in the
quiet late-Asia / London-open windows. Principled fixed params (no mining), and the
decisive question: taker (pay spread) vs maker (earn spread), in-sample vs out-of-sample.

Geometry matched to the lag-1 autocorr finding: fade a 1-2 bar overshoot, capture a
FRACTION of it (not the full mean), bounded stop, short time-stop. Costs swept from
+0.30 (cross the spread) down through 0 to -0.10 (provide liquidity / earn half-spread).
"""
import csv, numpy as np

CSV="reports/xau_m5_3y.csv"
LB=2            # overshoot lookback (bars)
K=1.2           # entry: |move| >= K * rolling std of the LB-move
TARGET_F=0.5    # capture 50% of the overshoot (the snap, not the full mean)
STOP_F=1.5      # stop at 1.5x the overshoot beyond entry (bounds the tail)
TIME=6          # bars max hold
COSTS=(0.30,0.20,0.10,0.0,-0.10)   # >0 taker pays, <0 maker earns

def load(p):
    t,o,c,h,l=[],[],[],[],[]
    with open(p,encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(r["time"]); o.append(float(r["o"])); c.append(float(r["c"]))
            h.append(float(r["h"])); l.append(float(r["l"]))
    hour=np.array([int(x[11:13]) for x in t])
    yr=np.array([int(x[:4]) for x in t])
    return np.array(o),np.array(c),np.array(h),np.array(l),hour,yr

o,c,h,l,hour,yr=load(CSV)
n=len(c); ret=np.diff(c,prepend=c[0])

# rolling std of the LB-bar move (for entry threshold) and rolling vol regime
mv=np.full(n,np.nan); mv[LB:]=c[LB:]-c[:-LB]
sd=np.full(n,np.nan)
W=200; mv2=np.where(np.isfinite(mv),mv*mv,0.0); cs=np.cumsum(mv2); cnt=np.cumsum(np.isfinite(mv).astype(float))
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
ar=np.abs(ret); arc=np.cumsum(ar); rv=np.full(n,np.nan)
for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
vmed=np.nanmedian(rv)

WINDOWS={
 "LateAsia/LonOpen 3-9": lambda hh:(hh>=3)&(hh<=9),
 "London 8-12":          lambda hh:(hh>=8)&(hh<=12),
 "EarlyAsia 0-2 (ctrl)": lambda hh:(hh>=0)&(hh<=2),
}

def simulate(win_fn, lowtempo_only=True):
    trades=[]
    i=W+1
    while i<n-1:
        if not (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and win_fn(hour[i])):
            i+=1; continue
        if lowtempo_only and not (np.isfinite(rv[i]) and rv[i]<vmed):
            i+=1; continue
        if abs(mv[i])<K*sd[i]:
            i+=1; continue
        side=-1 if mv[i]>0 else 1
        entry=c[i]; ov=abs(mv[i])
        target=entry+side*TARGET_F*ov
        stop=entry-side*STOP_F*ov
        ex=None
        for j in range(i+1,min(i+1+TIME,n)):
            if side>0:
                if l[j]<=stop: ex=stop; break
                if h[j]>=target: ex=target; break
            else:
                if h[j]>=stop: ex=stop; break
                if l[j]<=target: ex=target; break
        if ex is None: ex=c[min(i+TIME,n-1)]
        trades.append(((ex-entry)*side, yr[i]))
        i=(j if ex is not None else i+TIME)+1
    return trades

def stats(pts,cost):
    p=pts-cost
    if len(p)<20: return None
    wr=100*(p>0).mean(); exp=p.mean()
    gp=p[p>0].sum(); gl=-p[p<0].sum(); pf=gp/gl if gl>0 else np.inf
    return len(p),wr,exp,p.sum(),pf,np.sort(p)[:3]

print(f"params LB={LB} K={K} target={TARGET_F}xmove stop={STOP_F}xmove time={TIME}  vmed={vmed:.3f}")
print("IS = 2023-2024 (train view), OOS = 2025-2026 (held out, judged ONCE)\n")
for name,fn in WINDOWS.items():
    tr=simulate(fn)
    if not tr: print(f"[{name}] no trades"); continue
    pts=np.array([t[0] for t in tr]); ys=np.array([t[1] for t in tr])
    ism=ys<=2024; oos=ys>=2025
    print(f"[{name}]  total trades={len(pts)}  IS={ism.sum()} OOS={oos.sum()}")
    print(f"   {'cost':>6} | {'IS exp':>8} {'IS PF':>6} | {'OOS exp':>8} {'OOS WR':>6} {'OOS PF':>6} {'OOS net':>9}  worst3_OOS")
    for cost in COSTS:
        si=stats(pts[ism],cost); so=stats(pts[oos],cost)
        if not si or not so: continue
        tag=" (maker)" if cost<0 else (" (taker)" if cost>0 else "")
        print(f"   {cost:>6.2f} | {si[2]:>+8.3f} {si[4]:>6.2f} | {so[2]:>+8.3f} {so[1]:>5.1f}% {so[4]:>6.2f} {so[3]:>+9.1f}  {so[5].round(1)}{tag}")
    print()
print("DONE")
