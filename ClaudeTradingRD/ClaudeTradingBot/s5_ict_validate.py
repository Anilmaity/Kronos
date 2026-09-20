"""Walk-forward / robustness validation of the Daily-ICT-bias snap-fade maker, plus a
same-period comparison vs the real account (Jun 21-24, 2026). Parameter-free rule, so
per-period consistency IS the walk-forward test. Reuses bias+sim logic from s5_snap_ict.
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.2;W=200;OFFSET=0.25;FILL_WIN=3;TARGET_F=0.5;STOP_F=1.5;TIME=6
SPREAD=0.20;HALF=0.10;USD=10.0;FRACT=2
t=[];c=[];h=[];l=[]
for r in csv.DictReader(open(CSV,encoding="utf-8")):
    t.append(r["time"]);c.append(float(r["c"]));h.append(float(r["h"]));l.append(float(r["l"]))
c=np.array(c);h=np.array(h);l=np.array(l);n=len(c);ret=np.diff(c,prepend=c[0])
hour=np.array([int(x[11:13]) for x in t])
mv=np.full(n,np.nan);mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0);cs=np.cumsum(mv2);cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
ar=np.abs(ret);arc=np.cumsum(ar);rv=np.full(n,np.nan)
for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
# CAUSAL rolling low-tempo threshold (trailing ~1 month), replaces global median (look-ahead)
WW=5760; rvf=np.where(np.isfinite(rv),rv,0.0); rvc=np.cumsum(rvf); fc=np.cumsum(np.isfinite(rv).astype(float))
thr=np.full(n,np.nan)
for i in range(WW,n):
    k=fc[i]-fc[i-WW]
    if k>500: thr[i]=(rvc[i]-rvc[i-WW])/k
WIN=lambda hh:(hh>=3)&(hh<=9)
def htf_bias_D1():
    keys=[];H=[];L=[];C=[];m5b=np.empty(n,int);idx={}
    for i in range(n):
        k=t[i][:10]
        if k not in idx: idx[k]=len(keys);keys.append(k);H.append(h[i]);L.append(l[i]);C.append(c[i])
        else: b=idx[k];H[b]=max(H[b],h[i]);L[b]=min(L[b],l[i]);C[b]=c[i]
        m5b[i]=idx[k]
    H=np.array(H);L=np.array(L);C=np.array(C);M=len(keys)
    cSH={};cSL={}
    for k in range(FRACT,M-FRACT):
        if H[k]==H[k-FRACT:k+FRACT+1].max() and H[k]>H[k-1] and H[k]>H[k+1]: cSH[k+FRACT]=H[k]
        if L[k]==L[k-FRACT:k+FRACT+1].min() and L[k]<L[k-1] and L[k]<L[k+1]: cSL[k+FRACT]=L[k]
    bias=np.zeros(M,int);sh=None;sl=None;b=0
    for k in range(M):
        if k in cSH: sh=cSH[k]
        if k in cSL: sl=cSL[k]
        if sh is not None and C[k]>sh: b=+1
        elif sl is not None and C[k]<sl: b=-1
        bias[k]=b
    out=np.zeros(n,int)
    for i in range(n): out[i]=bias[m5b[i]-1] if m5b[i]-1>=0 else 0
    return out
bias=htf_bias_D1()
def cand(i):
    return (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and WIN(hour[i])
            and np.isfinite(rv[i]) and np.isfinite(thr[i]) and rv[i]<thr[i] and abs(mv[i])>=K*sd[i])
def run(direction=+1,t0=None,t1=None):
    out=[];i=W+1
    while i<n-2:
        if not cand(i): i+=1;continue
        if t0 is not None and not(t0<=t[i]<=t1): i+=1;continue
        up=mv[i]>0;side=-1 if up else 1;ov=abs(mv[i]);want=side*direction
        if bias[i]==0 or np.sign(want)!=bias[i]: i+=1;continue
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
        out.append(((ex-entry)*side+HALF+(HALF if mk else -HALF),t[i]));i=j+1
    return out
def stat(rows,t0,t1):
    p=np.array([r[0] for r in rows if t0<=r[1][:10]<=t1])
    if len(p)<1: return None
    gp=p[p>0].sum();gl=-p[p<0].sum()
    return len(p),100*(p>0).mean(),p.sum()*USD,(gp/gl if gl>0 else float('inf'))
wt=run(+1);ag=run(-1)
print("=== WALK-FORWARD by year — Daily-ICT-bias snap-fade (with-trend) vs control ===")
print(f"{'period':16s} | {'WITH-trend':>34s} | {'AGAINST (control)':>34s}")
for lab,a,b in [("2023","2023-01-01","2023-12-31"),("2024","2024-01-01","2024-12-31"),
                ("2025 (OOS)","2025-01-01","2025-12-31"),("2026 YTD (OOS)","2026-01-01","2026-12-31")]:
    w=stat(wt,a,b);g=stat(ag,a,b)
    ws=f"n={w[0]:4d} WR={w[1]:3.0f}% ${w[2]:>+7,.0f} PF={w[3]:.2f}" if w else "n=0"
    gs=f"n={g[0]:4d} WR={g[1]:3.0f}% ${g[2]:>+7,.0f} PF={g[3]:.2f}" if g else "n=0"
    print(f"{lab:16s} | {ws:>34s} | {gs:>34s}")
print("\n=== SAME-PERIOD comparison vs real account ===")
for lab,a,b in [("Order window Jun21-24","2026-06-21","2026-06-24"),("Last week Jun18-24","2026-06-18","2026-06-24")]:
    w=stat(wt,a,b)
    print(f"  {lab:24s} model: " + (f"n={w[0]} WR={w[1]:.0f}% ${w[2]:+,.0f} PF={w[3]:.2f}" if w else "n=0 (no setup)"))
print("  Real account Jun21-24    : n=67 WR=92.5% +$452.44 PF=20.84  (no stop, all hours)")
print("DONE")
