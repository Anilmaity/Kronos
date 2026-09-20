"""Session comparison on the VALIDATED snap_ict_maker model (maker, daily ICT bias,
causal low-tempo, proportional stop). Only the trading session window changes. Walk-forward
by year so we see whether more sessions keep the edge or dilute it.

Sessions (UTC):  Asia 0-7 | London 7-13 | New York 13-22
Configs:
  A) 03-09 (validated)              {3..9}
  B) 03-09 + NY reversion 17-22     {3..9, 17..22}
  C) ALL THREE sessions             {0..22}
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.2;W=200;OFFSET=0.25;FILL_WIN=3;TARGET_F=0.5;STOP_F=1.5;TIME=6
SPREAD=0.20;HALF=0.10;USD=10.0;FRACT=2;LOWTEMPO_WIN=5760
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
rvf=np.where(np.isfinite(rv),rv,0.0);rvc=np.cumsum(rvf);fc=np.cumsum(np.isfinite(rv).astype(float))
thr=np.full(n,np.nan)
for i in range(LOWTEMPO_WIN,n):
    k=fc[i]-fc[i-LOWTEMPO_WIN]
    if k>500: thr[i]=(rvc[i]-rvc[i-LOWTEMPO_WIN])/k
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

def backtest(sess):
    out=[];i=W+1
    while i<n-2:
        if not(np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and hour[i] in sess
               and np.isfinite(rv[i]) and np.isfinite(thr[i]) and rv[i]<thr[i] and abs(mv[i])>=K*sd[i]):
            i+=1;continue
        up=mv[i]>0;side=-1 if up else 1;ov=abs(mv[i])
        if bias[i]==0 or np.sign(side)!=bias[i]: i+=1;continue
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
def stat(rows,a,b):
    p=np.array([r[0] for r in rows if a<=r[1][:10]<=b])
    if len(p)<1: return None
    gp=p[p>0].sum();gl=-p[p<0].sum()
    return len(p),100*(p>0).mean(),p.sum()*USD,(gp/gl if gl>0 else float('inf'))

CONFIGS=[("A) 03-09 validated",set(range(3,10))),
         ("B) 03-09 + NY 17-22",set(range(3,10))|set(range(17,23))),
         ("C) ALL 3 sessions 00-22",set(range(0,23)))]
for name,sess in CONFIGS:
    tr=backtest(sess)
    print(f"\n=== {name}  (hours={sorted(sess)[0]}..{sorted(sess)[-1]}) ===")
    tot=0
    for y in ("2023","2024","2025","2026"):
        s=stat(tr,f"{y}-01-01",f"{y}-12-31")
        if s: print(f"   {y}: n={s[0]:4d} WR={s[1]:4.0f}% net=${s[2]:>+7,.0f} PF={s[3]:.2f}");tot+=s[2]
    print(f"   TOTAL net=${tot:+,.0f}")
print("\nDONE")
