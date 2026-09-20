"""HIGH-WIN-RATE fade, built to feel like the mobile-scalp account (tiny TP, wide stop,
all hours). Shown across consecutive ~2-month windows in 2025-2026 so the win rate AND
the P&L are both visible. Taker, spread 0.20pt, $10/pt @0.10 lot.

The point this answers: 'give me high WR over 1-2 months like my trades.' Easy to hit.
The question it forces: does high WR over a short window mean repeatable profit?
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.0;W=200;TP=0.5;SL=10.0;TIME=120;SPREAD=0.20;USD=10.0   # tiny TP, wide stop = high WR
t=[];c=[];h=[];l=[]
for r in csv.DictReader(open(CSV,encoding="utf-8")):
    t.append(r["time"]);c.append(float(r["c"]));h.append(float(r["h"]));l.append(float(r["l"]))
c=np.array(c);h=np.array(h);l=np.array(l);n=len(c)
mv=np.full(n,np.nan);mv[LB:]=c[LB:]-c[:-LB]
mv2=np.where(np.isfinite(mv),mv*mv,0.0);cs=np.cumsum(mv2);cnt=np.cumsum(np.isfinite(mv).astype(float))
sd=np.full(n,np.nan)
for i in range(W,n):
    k=cnt[i]-cnt[i-W]
    if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)

def run(d0,d1):
    out=[];i=W+1
    while i<n-2:
        if not(d0<=t[i][:10]<=d1): i+=1;continue
        if not(np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and abs(mv[i])>=K*sd[i]): i+=1;continue
        up=mv[i]>0;side=-1 if up else 1;entry=c[i]
        tp=entry-TP if up else entry+TP; st=entry+SL if up else entry-SL
        ex=None
        for j in range(i+1,min(i+1+TIME,n)):
            if up:
                if h[j]>=st: ex=st;break
                if l[j]<=tp: ex=tp;break
            else:
                if l[j]<=st: ex=st;break
                if h[j]>=tp: ex=tp;break
        if ex is None: ex=c[min(i+TIME,n-1)]
        out.append((ex-entry)*side-SPREAD);i=j+1
    return np.array(out)

wins_table=[
 ("2025 Jan-Feb","2025-01-01","2025-02-28"),
 ("2025 Mar-Apr","2025-03-01","2025-04-30"),
 ("2025 May-Jun","2025-05-01","2025-06-30"),
 ("2025 Jul-Aug","2025-07-01","2025-08-31"),
 ("2025 Sep-Oct","2025-09-01","2025-10-31"),
 ("2025 Nov-Dec","2025-11-01","2025-12-31"),
 ("2026 Jan-Feb","2026-01-01","2026-02-28"),
 ("2026 Mar-Apr","2026-03-01","2026-04-30"),
 ("2026 May-Jun","2026-05-01","2026-06-24"),
]
print(f"HIGH-WR fade  (TP={TP} SL={SL} all-hours)  — same model, each ~2-month window:\n")
print(f"{'window':14s} {'trades':>6} {'WR':>6} {'net$':>9} {'worstTrade$':>12} {'wins_erased_by_worst':>20}")
for lab,a,b in wins_table:
    p=run(a,b)
    if len(p)<5: print(f"{lab:14s} {len(p):>6}   --");continue
    wr=100*(p>0).mean();net=p.sum()*USD;worst=p.min()*USD
    avgwin=p[p>0].mean()*USD if (p>0).any() else 0
    erased=abs(worst)/avgwin if avgwin>0 else float('inf')
    print(f"{lab:14s} {len(p):>6} {wr:>5.1f}% {net:>+9.0f} {worst:>12.0f} {erased:>19.1f}x")
print("\n(High WR every window. Watch net$ flip sign and the single worst trade.)")
