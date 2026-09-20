"""Add a HIGHER-TIMEFRAME BIAS to the snap-fade maker model and compare to baseline.

Base = §5 model: 03-09 UTC, low-tempo, K=1.2 overshoot, maker w/ adverse selection,
spread 0.20pt, $10/pt. OOS baseline was -$137.

HTF bias (computed causally on M5 via EMA crossover):
  HTF-A (H4-ish): EMA(24) vs EMA(96)     bias_up if fast>slow
  HTF-B (D1-ish): EMA(96) vs EMA(288)
WITH-trend filter: take a fade ONLY if its side agrees with the HTF bias
  (buy-fade only in an uptrend, sell-fade only in a downtrend) -> skips fading INTO trend.
AGAINST-trend shown as a sanity check (should be worse).
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.2;W=200;OFFSET=0.25;FILL_WIN=3;TARGET_F=0.5;STOP_F=1.5;TIME=6
SPREAD=0.20;HALF=0.10;USD=10.0
t=[];c=[];h=[];l=[]
for r in csv.DictReader(open(CSV,encoding="utf-8")):
    t.append(r["time"]);c.append(float(r["c"]));h.append(float(r["h"]));l.append(float(r["l"]))
c=np.array(c);h=np.array(h);l=np.array(l);n=len(c);ret=np.diff(c,prepend=c[0])
yr=np.array([int(x[:4]) for x in t]);hour=np.array([int(x[11:13]) for x in t])
mv=np.full(n,np.nan);mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0);cs=np.cumsum(mv2);cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
ar=np.abs(ret);arc=np.cumsum(ar);rv=np.full(n,np.nan)
for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
vmed=np.nanmedian(rv)
def ema(x,span):
    a=2/(span+1);y=np.empty_like(x);y[0]=x[0]
    for i in range(1,len(x)): y[i]=a*x[i]+(1-a)*y[i-1]
    return y
biasA=np.sign(ema(c,24)-ema(c,96))   # H4-ish
biasB=np.sign(ema(c,96)-ema(c,288))  # D1-ish
WIN=lambda hh:(hh>=3)&(hh<=9)
def cand(i):
    return (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and WIN(hour[i])
            and np.isfinite(rv[i]) and rv[i]<vmed and abs(mv[i])>=K*sd[i])

def maker(bias=None,direction=+1):
    """bias array or None; direction +1=with-trend, -1=against-trend."""
    out=[];i=W+1
    while i<n-2:
        if not cand(i): i+=1; continue
        up=mv[i]>0; side=-1 if up else 1; ov=abs(mv[i])
        if bias is not None:
            want = side*direction            # with-trend: fade side should equal bias
            if bias[i]==0 or np.sign(want)!=bias[i]: i+=1; continue
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
        pnl=(ex-entry)*side+HALF+(HALF if mk else -HALF)
        out.append((pnl,yr[i])); i=j+1
    return out

def line(name,rows):
    def blk(p):
        if len(p)<1: return "n=   0"
        gp=p[p>0].sum();gl=-p[p<0].sum();pf=gp/gl if gl>0 else float('inf')
        return f"n={len(p):4d} WR={100*(p>0).mean():4.0f}% PnL=${p.sum()*USD:>+7,.0f} PF={pf:.2f}"
    isp=np.array([r[0] for r in rows if r[1]<=2024]);oosp=np.array([r[0] for r in rows if r[1]>=2025])
    allp=np.array([r[0] for r in rows])
    print(f"  {name:30s} | IS  {blk(isp)} | OOS {blk(oosp)} | FULL {blk(allp)}")

print("=== HIGHER-TIMEFRAME BIAS on the snap-fade maker model (03-09, low-tempo) ===\n")
line("Baseline (no HTF bias)",        maker())
line("HTF-A H4 with-trend",           maker(biasA,+1))
line("HTF-A H4 against-trend (sanity)",maker(biasA,-1))
line("HTF-B D1 with-trend",           maker(biasB,+1))
line("HTF-B D1 against-trend (sanity)",maker(biasB,-1))
print("\nDONE")
