"""Adverse-selection-honest version of the late-Asia/London snap-fade.

The optimistic test entered at market the instant an overshoot printed, then assumed the
reversion. A real liquidity provider does NOT get that. Here we model a PASSIVE LIMIT:

  up-overshoot  -> post a SELL limit ABOVE price (provide liquidity into the move).
  down-overshoot-> post a BUY  limit BELOW price.
  Fill ONLY if a later bar trades through the resting price within FILL_WIN bars.

This is where adverse selection enters automatically: you get filled precisely on the
bars where price CONTINUED to your level (ran further), and you simply MISS the clean
reversions that turn before reaching you. Maker credit (earning ~half the spread) is
swept, because whether the account can be a maker at all is the real-world unknown.

Fixed geometry, no mining. Held-out OOS (2025-26) judged once. Control = early-Asia 0-2.
"""
import csv, numpy as np

CSV="reports/xau_m5_3y.csv"
LB=2; K=1.2; W=200
OFFSET=0.25      # post this many sigma BEYOND the overshoot close (passive into the move)
FILL_WIN=3       # bars the limit rests before cancel
TARGET_F=0.5     # cover after retracing 50% of the original move
STOP_F=1.5       # stop 1.5*move beyond fill (bounds tail)
TIME=6           # bars to manage after fill
CREDITS=(-0.20,0.0,0.05,0.10,0.15)   # <0 = taker(pay); >=0 maker spread capture

def load(p):
    t,o,c,h,l=[],[],[],[],[]
    with open(p,encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(r["time"]); o.append(float(r["o"])); c.append(float(r["c"]))
            h.append(float(r["h"])); l.append(float(r["l"]))
    hour=np.array([int(x[11:13]) for x in t]); yr=np.array([int(x[:4]) for x in t])
    return np.array(o),np.array(c),np.array(h),np.array(l),hour,yr

o,c,h,l,hour,yr=load(CSV)
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

WINDOWS={"LateAsia/LonOpen 3-9": lambda hh:(hh>=3)&(hh<=9),
         "EarlyAsia 0-2 (ctrl)": lambda hh:(hh>=0)&(hh<=2)}

def simulate(win_fn):
    posted=0; filled=[]
    i=W+1
    while i<n-2:
        if not (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and win_fn(hour[i])
                and np.isfinite(rv[i]) and rv[i]<vmed and abs(mv[i])>=K*sd[i]):
            i+=1; continue
        posted+=1
        up=mv[i]>0; side=-1 if up else 1            # fade
        L = c[i] + (OFFSET*sd[i] if up else -OFFSET*sd[i])   # passive limit beyond
        # try to fill within FILL_WIN bars
        fj=None
        for j in range(i+1,min(i+1+FILL_WIN,n)):
            if up and h[j]>=L: fj=j; break
            if (not up) and l[j]<=L: fj=j; break
        if fj is None: i+=1; continue                # missed -> no trade (the good reversions)
        entry=L; ov=abs(mv[i])
        target = entry - TARGET_F*ov if up else entry + TARGET_F*ov   # cover toward pre-move
        stop   = entry + STOP_F*ov   if up else entry - STOP_F*ov     # bound the tail
        ex=None
        for j in range(fj+1,min(fj+1+TIME,n)):
            if up:   # we are SHORT: profit if price falls to target, stop if rises
                if h[j]>=stop: ex=stop; break
                if l[j]<=target: ex=target; break
            else:    # LONG
                if l[j]<=stop: ex=stop; break
                if h[j]>=target: ex=target; break
        if ex is None: ex=c[min(fj+TIME,n-1)]
        pts=(ex-entry)*side
        filled.append((pts,yr[i]))
        i=j+1
    return posted,filled

def stats(pts,credit):
    p=pts+credit
    if len(p)<20: return None
    wr=100*(p>0).mean(); exp=p.mean()
    gp=p[p>0].sum(); gl=-p[p<0].sum(); pf=gp/gl if gl>0 else np.inf
    return len(p),wr,exp,p.sum(),pf,np.sort(p)[:3]

print(f"PASSIVE-LIMIT maker model | OFFSET={OFFSET}sigma fill_win={FILL_WIN} "
      f"target={TARGET_F}xmove stop={STOP_F}xmove time={TIME}")
print("IS=2023-24  OOS=2025-26 (held out, judged once)\n")
for name,fn in WINDOWS.items():
    posted,fl=simulate(fn)
    if not fl: print(f"[{name}] no fills"); continue
    pts=np.array([t[0] for t in fl]); ys=np.array([t[1] for t in fl])
    fillrate=100*len(fl)/posted
    ism=ys<=2024; oos=ys>=2025
    print(f"[{name}]  posted={posted}  filled={len(fl)} (fill-rate {fillrate:.0f}%)  IS={ism.sum()} OOS={oos.sum()}")
    print(f"   {'credit':>7} | {'IS exp':>8} {'IS PF':>6} | {'OOS exp':>8} {'OOS WR':>6} {'OOS PF':>6} {'OOS net':>9}  worst3_OOS")
    for cr in CREDITS:
        si=stats(pts[ism],cr); so=stats(pts[oos],cr)
        if not si or not so: continue
        tag=" taker" if cr<0 else (" maker" if cr>0 else "")
        print(f"   {cr:>+7.2f} | {si[2]:>+8.3f} {si[4]:>6.2f} | {so[2]:>+8.3f} {so[1]:>5.1f}% {so[4]:>6.2f} {so[3]:>+9.1f}  {so[5].round(1)}{tag}")
    print()
print("DONE")
