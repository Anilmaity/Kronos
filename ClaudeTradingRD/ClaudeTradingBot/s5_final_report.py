"""Consolidated stats for the candidate model (late-Asia/London snap-fade, real 0.20pt
spread) -> feeds the written report. Prints total trades, win rate, total PnL (pt and $),
PF, expectancy, max drawdown, worst trade, for TAKER vs MAKER, FULL/IS/OOS.
$ assumes 0.10 lot on XAUUSD => $10 per 1.0 pt price move.
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.2;W=200;OFFSET=0.25;FILL_WIN=3;TARGET_F=0.5;STOP_F=1.5;TIME=6
SPREAD=0.20;HALF=SPREAD/2;USD_PER_PT=10.0  # 0.10 lot

def load(p):
    t,c,h,l=[],[],[],[]
    with open(p,encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(r["time"]);c.append(float(r["c"]));h.append(float(r["h"]));l.append(float(r["l"]))
    return (np.array(c),np.array(h),np.array(l),
            np.array([int(x[11:13]) for x in t]),np.array([int(x[:4]) for x in t]))
c,h,l,hour,yr=load(CSV); n=len(c); ret=np.diff(c,prepend=c[0])
mv=np.full(n,np.nan); mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0); cs=np.cumsum(mv2); cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
ar=np.abs(ret);arc=np.cumsum(ar);rv=np.full(n,np.nan)
for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
vmed=np.nanmedian(rv); WIN=lambda hh:(hh>=3)&(hh<=9)
def cand(i):
    return (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and WIN(hour[i])
            and np.isfinite(rv[i]) and rv[i]<vmed and abs(mv[i])>=K*sd[i])

def sim(mode):  # 'taker' or 'maker'
    out=[];i=W+1
    while i<n-2:
        if not cand(i): i+=1; continue
        up=mv[i]>0; side=-1 if up else 1; ov=abs(mv[i])
        if mode=="taker":
            entry=c[i]; fj=i
        else:
            L=c[i]+(OFFSET*sd[i] if up else -OFFSET*sd[i]); fj=None
            for j in range(i+1,min(i+1+FILL_WIN,n)):
                if up and h[j]>=L: fj=j; break
                if (not up) and l[j]<=L: fj=j; break
            if fj is None: i+=1; continue
            entry=L
        target=entry-TARGET_F*ov if up else entry+TARGET_F*ov
        stop  =entry+STOP_F*ov   if up else entry-STOP_F*ov
        ex=None;maker_exit=False
        for j in range(fj+1,min(fj+1+TIME,n)):
            if up:
                if h[j]>=stop: ex=stop;break
                if l[j]<=target: ex=target;maker_exit=True;break
            else:
                if l[j]<=stop: ex=stop;break
                if h[j]>=target: ex=target;maker_exit=True;break
        if ex is None: ex=c[min(fj+TIME,n-1)]
        raw=(ex-entry)*side
        pnl = raw-SPREAD if mode=="taker" else raw+HALF+(HALF if maker_exit else -HALF)
        out.append((pnl,yr[i])); i=j+1
    return out

def block(rows,lo,hi):
    p=np.array([r[0] for r in rows if lo<=r[1]<=hi])
    if len(p)==0: return None
    wins=p[p>0]; losses=p[p<0]
    eq=np.cumsum(p); peak=np.maximum.accumulate(eq); mdd=(eq-peak).min()
    return dict(n=len(p),wr=100*(p>0).mean(),pnl=p.sum(),usd=p.sum()*USD_PER_PT,
        exp=p.mean(),aw=wins.mean() if len(wins) else 0,al=losses.mean() if len(losses) else 0,
        pf=(wins.sum()/-losses.sum()) if len(losses) and losses.sum()<0 else float('inf'),
        mdd=mdd,mdd_usd=mdd*USD_PER_PT,worst=p.min())

print(f"# CANDIDATE MODEL — late-Asia/London snap-fade | spread={SPREAD}pt | $/pt={USD_PER_PT} (0.10 lot)\n")
for mode in ("taker","maker"):
    rows=sim(mode)
    print(f"## {mode.upper()}")
    for lab,lo,hi in (("FULL 2023-26",2023,2026),("IN-SAMPLE 2023-24",2023,2024),("OUT-OF-SAMPLE 2025-26",2025,2026)):
        b=block(rows,lo,hi)
        if not b: continue
        print(f"  {lab:22s} trades={b['n']:4d}  WR={b['wr']:4.1f}%  totPnL={b['pnl']:+8.1f}pt (${b['usd']:+,.0f})"
              f"  exp={b['exp']:+.3f}pt  PF={b['pf']:.2f}  avgW={b['aw']:+.2f} avgL={b['al']:+.2f}"
              f"  maxDD=${b['mdd_usd']:,.0f}  worst={b['worst']:+.1f}pt")
    print()
print("DONE")
