"""ICT HTF MARKET STRUCTURE BIAS on the snap-fade maker model (replaces the EMA proxy).

Bias is built from real structure, causally:
  1. Resample M5 -> HTF candles (H4 buckets at 0/4/8/12/16/20 UTC; or Daily).
  2. Swing highs/lows via fractal (N bars lower/higher each side); a swing becomes
     KNOWN only N bars later (causal confirmation).
  3. BOS/CHoCH state machine on candle BODY CLOSE (ICT confirmation standard):
     close > last known swing high -> bias bullish (+1);
     close < last known swing low  -> bias bearish (-1); else carry forward.
     (A close beyond the opposite swing IS the CHoCH that flips bias.)
  4. Each M5 bar uses the bias of the most recent FULLY CLOSED HTF candle.
WITH-trend filter: fade only when fade side agrees with HTF bias (buy dips in bullish
structure, sell rips in bearish). against-trend shown as control. Baseline = §5 model.
"""
import csv, numpy as np
CSV="reports/xau_m5_3y.csv"
LB=2;K=1.2;W=200;OFFSET=0.25;FILL_WIN=3;TARGET_F=0.5;STOP_F=1.5;TIME=6
SPREAD=0.20;HALF=0.10;USD=10.0;FRACT=2
t=[];o=[];c=[];h=[];l=[]
for r in csv.DictReader(open(CSV,encoding="utf-8")):
    t.append(r["time"]);o.append(float(r["o"]));c.append(float(r["c"]));h.append(float(r["h"]));l.append(float(r["l"]))
o=np.array(o);c=np.array(c);h=np.array(h);l=np.array(l);n=len(c);ret=np.diff(c,prepend=c[0])
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
WIN=lambda hh:(hh>=3)&(hh<=9)

def bucket_key(ts,mode):
    d=ts[:10]
    if mode=="D1": return d
    return d+"_"+str(int(ts[11:13])//4)   # H4

def htf_bias(mode):
    # build HTF OHLC per bucket in order
    keys=[];H=[];L=[];C=[];m5_bucket=np.empty(n,dtype=int)
    idx={}
    for i in range(n):
        k=bucket_key(t[i],mode)
        if k not in idx:
            idx[k]=len(keys);keys.append(k);H.append(h[i]);L.append(l[i]);C.append(c[i])
        else:
            b=idx[k];H[b]=max(H[b],h[i]);L[b]=min(L[b],l[i]);C[b]=c[i]   # close = last m5 close in bucket
        m5_bucket[i]=idx[k]
    H=np.array(H);L=np.array(L);C=np.array(C);M=len(keys)
    # fractal swings, confirmed FRACT bars later
    conf_SH={}; conf_SL={}  # confirmation_index -> price
    for k in range(FRACT,M-FRACT):
        if H[k]==H[k-FRACT:k+FRACT+1].max() and H[k]>H[k-1] and H[k]>H[k+1]:
            conf_SH[k+FRACT]=H[k]
        if L[k]==L[k-FRACT:k+FRACT+1].min() and L[k]<L[k-1] and L[k]<L[k+1]:
            conf_SL[k+FRACT]=L[k]
    bias=np.zeros(M,int); last_SH=None; last_SL=None; b=0
    for k in range(M):
        if k in conf_SH: last_SH=conf_SH[k]
        if k in conf_SL: last_SL=conf_SL[k]
        if last_SH is not None and C[k]>last_SH: b=+1
        elif last_SL is not None and C[k]<last_SL: b=-1
        bias[k]=b
    # map to M5: use PREVIOUS closed HTF bucket
    out=np.zeros(n,int)
    for i in range(n):
        bk=m5_bucket[i]
        out[i]=bias[bk-1] if bk-1>=0 else 0
    return out

def cand(i):
    return (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and WIN(hour[i])
            and np.isfinite(rv[i]) and rv[i]<vmed and abs(mv[i])>=K*sd[i])

def maker(bias=None,direction=+1):
    out=[];i=W+1
    while i<n-2:
        if not cand(i): i+=1; continue
        up=mv[i]>0; side=-1 if up else 1; ov=abs(mv[i])
        if bias is not None:
            want=side*direction
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
        out.append(((ex-entry)*side+HALF+(HALF if mk else -HALF),yr[i])); i=j+1
    return out

def line(name,rows):
    def blk(p):
        if len(p)<1: return "n=   0"
        gp=p[p>0].sum();gl=-p[p<0].sum();pf=gp/gl if gl>0 else float('inf')
        return f"n={len(p):4d} WR={100*(p>0).mean():4.0f}% PnL=${p.sum()*USD:>+7,.0f} PF={pf:.2f}"
    isp=np.array([r[0] for r in rows if r[1]<=2024]);oosp=np.array([r[0] for r in rows if r[1]>=2025])
    allp=np.array([r[0] for r in rows])
    print(f"  {name:32s} | IS  {blk(isp)} | OOS {blk(oosp)} | FULL {blk(allp)}")

biasH4=htf_bias("H4"); biasD1=htf_bias("D1")
print("=== ICT HTF MARKET-STRUCTURE BIAS on snap-fade maker (03-09, low-tempo) ===\n")
line("Baseline (no bias)",          maker())
line("ICT H4 bias  WITH-trend",     maker(biasH4,+1))
line("ICT H4 bias  against (ctrl)", maker(biasH4,-1))
line("ICT D1 bias  WITH-trend",     maker(biasD1,+1))
line("ICT D1 bias  against (ctrl)", maker(biasD1,-1))
print("\nDONE")
