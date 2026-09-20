"""Same snap-model variants over LAST WEEK (last 7 days of M5 data: 2026-06-18..06-24).
Maker spread 0.20, $10/pt (0.10 lot). One week, tiny sample -> descriptive only.
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.2;W=200;OFFSET=0.25;FILL_WIN=3;TARGET_F=0.5;STOP_F=1.5;TIME=6
SPREAD=0.20;HALF=0.10;USD=10.0
P0,P1="2026-06-18 00:00:00","2026-06-24 23:55:00"
t=[];c=[];h=[];l=[];vol=[]
for r in csv.DictReader(open(CSV,encoding="utf-8")):
    t.append(r["time"]);c.append(float(r["c"]));h.append(float(r["h"]));l.append(float(r["l"]));vol.append(float(r["volume"]))
c=np.array(c);h=np.array(h);l=np.array(l);vol=np.array(vol);n=len(c)
ret=np.diff(c,prepend=c[0])
mv=np.full(n,np.nan);mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0);cs=np.cumsum(mv2);cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
ar=np.abs(ret);arc=np.cumsum(ar);rv=np.full(n,np.nan)
for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
vmed=np.nanmedian(rv)
vcum=np.cumsum(vol);vmean=np.full(n,np.nan)
for i in range(W,n): vmean[i]=(vcum[i]-vcum[i-W])/W
vratio=np.where(vmean>0,vol/vmean,np.nan)

def sim(mode,window=False,lowtempo=False,vlo=None,vhi=None):
    out=[];i=W+1
    while i<n-2:
        if not(P0<=t[i]<=P1): i+=1;continue
        hh=int(t[i][11:13])
        if window and not(3<=hh<=9): i+=1;continue
        if lowtempo and not(np.isfinite(rv[i]) and rv[i]<vmed): i+=1;continue
        if not(np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and abs(mv[i])>=K*sd[i]): i+=1;continue
        vr=vratio[i]
        if vlo is not None and not(np.isfinite(vr) and vr<vlo): i+=1;continue
        if vhi is not None and not(np.isfinite(vr) and vr>=vhi): i+=1;continue
        up=mv[i]>0;side=-1 if up else 1;ov=abs(mv[i])
        if mode=="taker": entry=c[i];fj=i
        else:
            L=c[i]+(OFFSET*sd[i] if up else -OFFSET*sd[i]);fj=None
            for j in range(i+1,min(i+1+FILL_WIN,n)):
                if up and h[j]>=L: fj=j;break
                if (not up) and l[j]<=L: fj=j;break
            if fj is None: i+=1;continue
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
        raw=(ex-entry)*side
        pnl=raw-SPREAD if mode=="taker" else raw+HALF+(HALF if mk else -HALF)
        out.append(pnl);i=j+1
    return np.array(out)

bars=sum(1 for x in t if P0<=x<=P1)
print(f"=== LAST WEEK {P0[:10]} .. {P1[:10]}  ({bars} M5 bars) — descriptive only ===")
print(f"{'variant':34s} {'trades':>6} {'WR':>6} {'PnL$':>9}")
for name,kw in [
 ("Maker — 03-09 window",      dict(mode='maker',window=True)),
 ("Maker — all hours",         dict(mode='maker')),
 ("Maker — 03-09, low-tempo",  dict(mode='maker',window=True,lowtempo=True)),
 ("Maker — 03-09, LOW-vol",    dict(mode='maker',window=True,vlo=1.0)),
 ("Maker — 03-09, HIGH-vol",   dict(mode='maker',window=True,vhi=1.3)),
 ("Taker — 03-09 window",      dict(mode='taker',window=True)),
 ("Taker — all hours",         dict(mode='taker')),
]:
    p=sim(**kw)
    if len(p)==0: print(f"{name:34s} {0:>6} {'--':>6} {'$0':>9}");continue
    print(f"{name:34s} {len(p):>6} {100*(p>0).mean():>5.0f}% {p.sum()*USD:>+9.0f}")
print("\nNOTE: one week, n very small -> descriptive snapshot, NOT statistical validation.")
