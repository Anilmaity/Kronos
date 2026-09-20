"""Honest diagnostic for the user's thesis: 'short-term noise mean-reverts at low tempo,
harvest the liquidity.' Two parts, NO model selection, FIXED params (no mining):

  PART A  Variance-Ratio + lag-1 autocorr of returns, overall and by hour-of-day.
          VR(k) < 1  => mean reversion (noise snaps back).  VR>1 => trending.
  PART B  z-score fade WITH A REAL STOP (skill strategy #1 params, untuned):
          enter fade when |z|>=2, target = mean (z=0), stop = z=+-3.5, time-stop.
          Report net-of-cost expectancy + WORST trades (the tail) split by
          session and by volatility regime ('tempo'). The question: is there ANY
          regime where net expectancy is positive once the tail is bounded?
"""
import csv, numpy as np

CSV = "reports/xau_m5_3y.csv"
N = 50            # SMA/std lookback for z-score (fixed, per skill)
Z_IN, Z_STOP = 2.0, 3.5
TIME_STOP = 60   # bars (=5h on M5)
COSTS = (0.20, 0.30, 0.40)   # round-trip cost in price points (spread+commission), sensitivity

def load(p):
    t,c,h,l=[],[],[],[]
    with open(p,encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(r["time"]); c.append(float(r["c"])); h.append(float(r["h"])); l.append(float(r["l"]))
    hour=np.array([int(x[11:13]) for x in t])
    return np.array(c),np.array(h),np.array(l),hour

c,h,l,hour=load(CSV)
ret=np.diff(c,prepend=c[0])
n=len(c)

# ---------- PART A: variance ratio + autocorrelation ----------
def var_ratio(r,k):
    r=r[np.isfinite(r)]
    if len(r)<k*5: return np.nan
    v1=np.var(r)
    agg=np.add.reduceat(r[:len(r)//k*k], np.arange(0,len(r)//k*k,k))
    vk=np.var(agg)
    return vk/(k*v1) if v1>0 else np.nan

def autocorr1(r):
    r=r[np.isfinite(r)]; r=r-r.mean()
    if len(r)<10: return np.nan
    return np.sum(r[1:]*r[:-1])/np.sum(r*r)

print("=== PART A: mean-reversion structure (VR<1 = noise reverts, >1 = trends) ===")
print(f"  whole sample  VR(2)={var_ratio(ret,2):.3f} VR(5)={var_ratio(ret,5):.3f} "
      f"VR(10)={var_ratio(ret,10):.3f}   lag1-autocorr={autocorr1(ret):+.4f}")
print("  by hour (UTC):  hour  VR2    VR5    ac1     #bars")
for hh in range(24):
    m=hour==hh
    if m.sum()<500: continue
    print(f"            {hh:02d}    {var_ratio(ret[m],2):.3f}  {var_ratio(ret[m],5):.3f}  "
          f"{autocorr1(ret[m]):+0.4f}  {m.sum():6d}")

# ---------- PART B: z-fade WITH stop, honest expectancy by regime ----------
sma=np.full(n,np.nan); std=np.full(n,np.nan)
csum=np.cumsum(c); csum2=np.cumsum(c*c)
for i in range(N,n):
    s=csum[i]-csum[i-N]; s2=csum2[i]-csum2[i-N]
    mu=s/N; sma[i]=mu; var=max(s2/N-mu*mu,1e-9); std[i]=np.sqrt(var)
z=(c-sma)/std
# realized vol regime (rolling 100-bar abs-return mean), low = 'low tempo'
rv=np.full(n,np.nan)
ar=np.abs(ret)
arc=np.cumsum(ar)
for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
vmed=np.nanmedian(rv)

def session(hh):
    if 0<=hh<7: return "Asia"
    if 7<=hh<13: return "London"
    return "NY"

# simulate
trades=[]  # (pnl_pts_signed, hour, lowtempo)
i=N+1
while i<n-1:
    if not np.isfinite(z[i]) or abs(z[i])<Z_IN or abs(z[i-1])>=Z_IN:
        i+=1; continue
    side=-1 if z[i]>0 else 1            # fade
    entry=c[i]; mu=sma[i]; sd=std[i]
    target=mu                            # z=0
    stop=mu+Z_STOP*sd if side<0 else mu-Z_STOP*sd
    ex=None
    for j in range(i+1,min(i+1+TIME_STOP,n)):
        if side>0:                       # long: profit if price rises to target
            if l[j]<=stop: ex=stop; break
            if h[j]>=target: ex=target; break
        else:                            # short
            if h[j]>=stop: ex=stop; break
            if l[j]<=target: ex=target; break
    if ex is None: ex=c[min(i+TIME_STOP,n-1)]
    pts=(ex-entry)*side
    trades.append((pts,hour[i], (rv[i]<vmed) if np.isfinite(rv[i]) else False))
    i=j+1                                # non-overlap

pts=np.array([t[0] for t in trades],float)
hh=np.array([t[1] for t in trades],int)
lt=np.array([bool(t[2]) for t in trades])
sess=np.array([session(x) for x in hh])

def report(name,mask,cost):
    p=pts[mask]-cost
    if len(p)<20: print(f"  {name:22s} n={len(p):5d}  (too few)"); return
    wr=100*(p>0).mean(); exp=p.mean(); net=p.sum()
    gp=p[p>0].sum(); gl=-p[p<0].sum(); pf=gp/gl if gl>0 else np.inf
    worst=np.sort(p)[:3]
    print(f"  {name:22s} n={len(p):5d}  WR={wr:4.1f}%  exp={exp:+.3f}pt  "
          f"net={net:+8.1f}pt  PF={pf:4.2f}  worst3={worst.round(1)}")

print(f"\n=== PART B: z-fade WITH stop (z_in={Z_IN}, z_stop={Z_STOP}, mean target), "
      f"untuned. vol-median={vmed:.3f}pt ===")
for cost in COSTS:
    print(f"\n  -- round-trip cost = {cost:.2f} pt --")
    report("ALL", np.ones(len(pts),bool), cost)
    report("LOW-TEMPO (vol<med)", lt, cost)
    report("HIGH-TEMPO (vol>=med)", ~lt, cost)
    for s in ("Asia","London","NY"):
        report(f"{s}", sess==s, cost)
    report("LOW-TEMPO & Asia", lt&(sess=="Asia"), cost)
print("\nDONE")
