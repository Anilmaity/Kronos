"""(A) Volume filter on the snap-fade maker model: fade only LOW-volume overshoots
(liquidity noise -> reverts) vs HIGH-volume (initiative/news -> continues).
(B) Run the SAME model over the exact period of the real account's 67 trades
(2026-06-21 22:00 -> 2026-06-24 00:05) for a head-to-head with the +$452 actual result.

Maker execution w/ adverse selection, spread 0.20pt, $10/pt (0.10 lot). OOS = 2025-26.
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.2;W=200;OFFSET=0.25;FILL_WIN=3;TARGET_F=0.5;STOP_F=1.5;TIME=6
SPREAD=0.20;HALF=SPREAD/2;USD=10.0

def load(p):
    t,c,h,l,v=[],[],[],[],[]
    with open(p,encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(r["time"]);c.append(float(r["c"]));h.append(float(r["h"]))
            l.append(float(r["l"]));v.append(float(r["volume"]))
    return (t,np.array(c),np.array(h),np.array(l),np.array(v),
            np.array([int(x[11:13]) for x in t]),np.array([int(x[:4]) for x in t]))
tm,c,h,l,vol,hour,yr=load(CSV); n=len(c); ret=np.diff(c,prepend=c[0])
mv=np.full(n,np.nan); mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0); cs=np.cumsum(mv2); cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
ar=np.abs(ret);arc=np.cumsum(ar);rv=np.full(n,np.nan)
for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
vmed=np.nanmedian(rv)
# causal rolling mean volume -> volume ratio
vcum=np.cumsum(vol); vmean=np.full(n,np.nan)
for i in range(W,n): vmean[i]=(vcum[i]-vcum[i-W])/W
vratio=np.where(vmean>0, vol/vmean, np.nan)
WIN=lambda hh:(hh>=3)&(hh<=9)

def cand(i):
    return (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and WIN(hour[i])
            and np.isfinite(rv[i]) and rv[i]<vmed and abs(mv[i])>=K*sd[i])

def maker(vol_lo=None,vol_hi=None,t_lo=None,t_hi=None):
    """vol_lo/hi filter on vratio[i]; t_lo/t_hi restrict to a time slice (string compare)."""
    out=[];i=W+1
    while i<n-2:
        if not cand(i): i+=1; continue
        if t_lo is not None and not (t_lo<=tm[i]<=t_hi): i+=1; continue
        vr=vratio[i]
        if vol_lo is not None and not (np.isfinite(vr) and vr<vol_lo): i+=1; continue
        if vol_hi is not None and not (np.isfinite(vr) and vr>=vol_hi): i+=1; continue
        up=mv[i]>0; side=-1 if up else 1; ov=abs(mv[i])
        L=c[i]+(OFFSET*sd[i] if up else -OFFSET*sd[i]); fj=None
        for j in range(i+1,min(i+1+FILL_WIN,n)):
            if up and h[j]>=L: fj=j; break
            if (not up) and l[j]<=L: fj=j; break
        if fj is None: i+=1; continue
        entry=L
        target=entry-TARGET_F*ov if up else entry+TARGET_F*ov
        stop  =entry+STOP_F*ov   if up else entry-STOP_F*ov
        ex=None;mk=False
        for j in range(fj+1,min(fj+1+TIME,n)):
            if up:
                if h[j]>=stop: ex=stop;break
                if l[j]<=target: ex=target;mk=True;break
            else:
                if l[j]<=stop: ex=stop;break
                if h[j]>=target: ex=target;mk=True;break
        if ex is None: ex=c[min(fj+TIME,n-1)]
        pnl=(ex-entry)*side + HALF + (HALF if mk else -HALF)
        out.append((pnl,yr[i])); i=j+1
    return out

def show(name,rows,lo=2023,hi=2026,split=True):
    def blk(p):
        if len(p)<1: return "n=0"
        gp=p[p>0].sum();gl=-p[p<0].sum();pf=gp/gl if gl>0 else float('inf')
        return f"n={len(p):4d} WR={100*(p>0).mean():4.1f}% exp={p.mean():+.3f}pt PnL=${p.sum()*USD:+,.0f} PF={pf:.2f}"
    allp=np.array([r[0] for r in rows])
    if not split:
        print(f"  {name:26s} {blk(allp)}"); return
    isp=np.array([r[0] for r in rows if r[1]<=2024]); oosp=np.array([r[0] for r in rows if r[1]>=2025])
    print(f"  {name:26s} IS[{blk(isp)}]  OOS[{blk(oosp)}]")

print("=== (A) VOLUME FILTER — maker model, 03-09 UTC window, IS 2023-24 / OOS 2025-26 ===")
show("ALL overshoots", maker())
show("LOW-vol  (vratio<1.0)", maker(vol_lo=1.0))
show("LOW-vol  (vratio<0.7)", maker(vol_lo=0.7))
show("HIGH-vol (vratio>=1.3)", maker(vol_hi=1.3))

print("\n=== (B) SAME MODEL over the real account's period 2026-06-21 22:00 -> 06-24 00:05 ===")
P0,P1="2026-06-21 22:00:00","2026-06-24 00:05:00"
show("model ALL-vol (this window)", maker(t_lo=P0,t_hi=P1), split=False)
show("model LOW-vol (this window)", maker(vol_lo=1.0,t_lo=P0,t_hi=P1), split=False)
print("  --- for reference: REAL ACCOUNT over this period = 67 trades, 92.5% WR, +$452.44 ---")
print("DONE")
