"""
SNAP-ICT-MAKER — XAUUSD short-horizon mean-reversion, gated by Daily ICT market-structure bias.

WHAT IT IS
  A liquidity-provision (maker) mean-reversion strategy that fades small intraday
  overshoots in the quiet late-Asia / London-open window, but ONLY in the direction of
  the higher-timeframe (Daily) ICT structural bias. Built from the forensic research in
  reports/REPORT-meanrev-snap-2026-06-26.md after the plain fade proved break-even and the
  Daily-ICT-bias filter turned it positive in every year tested.

RULES (all causal, no fitted parameters)
  Instrument / TF .... XAUUSD M5
  Session window ..... 03:00-09:00 UTC (late-Asia/London-open mean-reversion window)
  Low-tempo gate ..... trade only when rolling 100-bar realized vol < trailing ~1-month
                       average of it (quiet liquidity; CAUSAL threshold, no look-ahead)
  Daily ICT bias ..... fractal(2) swings on Daily candles -> BOS/CHoCH body-close state
                       machine -> bias +1 (bullish) / -1 (bearish). HTF outweighs LTF.
  Entry trigger ...... overshoot = |close - close[-2]| >= 1.2 * rolling std of that move
  Direction filter ... fade WITH the daily bias only (buy dips when bias +1, sell rips
                       when bias -1). Fading against the bias is -EV (see control).
  Execution .......... MAKER: passive limit 0.25 sigma beyond the overshoot, fill within
                       3 bars on continuation (adverse selection modeled).
  Target / stop ...... target = 50% retrace of the overshoot (limit, maker);
                       stop = 1.5x overshoot (market, taker); time-stop 6 bars.
  Cost model ......... spread 0.20 pt; +half-spread on maker fills, -half on market exits.

WALK-FORWARD (0.10 lot, $10/pt) — positive every year, control collapses 3 of 4:
  2023 +$285 PF1.08 | 2024 +$760 PF1.16 | 2025(OOS) +$186 PF1.02 | 2026YTD(OOS) +$1,525 PF1.32

CAVEATS — READ BEFORE TRADING
  * MAKER-DEPENDENT. As a taker (crossing the spread) this strategy LOSES. It requires an
    account that can post limit orders and earn/save the spread (raw-spread/ECN). On a
    spread-only CFD/challenge account it is NOT viable.
  * The daily-bias edge failed its control in 2023 (regime-dependent, not universal).
  * $ figures are modest at 0.10 lot; scale by risk, do not over-size to chase the target.
  * Validate live at minimum size before any real allocation. This is research output.
  * It deliberately sits out high-volatility bursts (e.g. it took 1 trade over the
    2026-06-21..24 window where the mobile-scalp account ran). That avoidance IS the design.
"""
import csv, numpy as np

# ---- parameters (fixed) ----
LB=2; K=1.2; W=200; OFFSET=0.25; FILL_WIN=3; TARGET_F=0.5; STOP_F=1.5; TIME=6
SPREAD=0.20; HALF=SPREAD/2; FRACT=2; LOWTEMPO_WIN=5760  # ~1 month of M5
SESSION=lambda hh: 3 <= hh <= 9

def load(path):
    t=[];o=[];c=[];h=[];l=[]
    with open(path,encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(r["time"]);o.append(float(r["o"]));c.append(float(r["c"]))
            h.append(float(r["h"]));l.append(float(r["l"]))
    return t,np.array(o),np.array(c),np.array(h),np.array(l)

def daily_ict_bias(t,c,h,l):
    """Causal Daily BOS/CHoCH bias mapped to each M5 bar (uses last CLOSED daily candle)."""
    n=len(c); keys=[];H=[];L=[];C=[];m5b=np.empty(n,int);idx={}
    for i in range(n):
        d=t[i][:10]
        if d not in idx: idx[d]=len(keys);keys.append(d);H.append(h[i]);L.append(l[i]);C.append(c[i])
        else: b=idx[d];H[b]=max(H[b],h[i]);L[b]=min(L[b],l[i]);C[b]=c[i]
        m5b[i]=idx[d]
    H=np.array(H);L=np.array(L);C=np.array(C);M=len(keys)
    cSH={};cSL={}
    for k in range(FRACT,M-FRACT):
        if H[k]==H[k-FRACT:k+FRACT+1].max() and H[k]>H[k-1] and H[k]>H[k+1]: cSH[k+FRACT]=H[k]
        if L[k]==L[k-FRACT:k+FRACT+1].min() and L[k]<L[k-1] and L[k]<L[k+1]: cSL[k+FRACT]=L[k]
    bias=np.zeros(M,int); sh=sl=None; b=0
    for k in range(M):
        if k in cSH: sh=cSH[k]
        if k in cSL: sl=cSL[k]
        if sh is not None and C[k]>sh: b=+1
        elif sl is not None and C[k]<sl: b=-1
        bias[k]=b
    return np.array([bias[m5b[i]-1] if m5b[i]-1>=0 else 0 for i in range(n)])

def indicators(t,c,h,l):
    n=len(c); ret=np.diff(c,prepend=c[0]); hour=np.array([int(x[11:13]) for x in t])
    mv=np.full(n,np.nan); mv[LB:]=c[LB:]-c[:-LB]
    mv2=np.where(np.isfinite(mv),mv*mv,0.0); cs=np.cumsum(mv2); cnt=np.cumsum(np.isfinite(mv).astype(float))
    sd=np.full(n,np.nan)
    for i in range(W,n):
        k=cnt[i]-cnt[i-W]
        if k>20: sd[i]=np.sqrt((cs[i]-cs[i-W])/k)
    ar=np.abs(ret); arc=np.cumsum(ar); rv=np.full(n,np.nan)
    for i in range(100,n): rv[i]=(arc[i]-arc[i-100])/100
    rvf=np.where(np.isfinite(rv),rv,0.0); rvc=np.cumsum(rvf); fc=np.cumsum(np.isfinite(rv).astype(float))
    thr=np.full(n,np.nan)
    for i in range(LOWTEMPO_WIN,n):
        k=fc[i]-fc[i-LOWTEMPO_WIN]
        if k>500: thr[i]=(rvc[i]-rvc[i-LOWTEMPO_WIN])/k
    return hour,mv,sd,rv,thr

def backtest(t,o,c,h,l, bias=None, direction=+1):
    """Returns list of (pnl_pt, time). direction +1 = with-bias (the strategy)."""
    n=len(c); hour,mv,sd,rv,thr=indicators(t,c,h,l)
    if bias is None: bias=daily_ict_bias(t,c,h,l)
    out=[]; i=W+1
    while i<n-2:
        ok=(np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i]>0 and SESSION(hour[i])
            and np.isfinite(rv[i]) and np.isfinite(thr[i]) and rv[i]<thr[i] and abs(mv[i])>=K*sd[i])
        if not ok: i+=1; continue
        up=mv[i]>0; side=-1 if up else 1; ov=abs(mv[i]); want=side*direction
        if bias[i]==0 or np.sign(want)!=bias[i]: i+=1; continue
        L=c[i]+(OFFSET*sd[i] if up else -OFFSET*sd[i]); fj=None
        for j in range(i+1,min(i+1+FILL_WIN,n)):
            if up and h[j]>=L: fj=j; break
            if (not up) and l[j]<=L: fj=j; break
        if fj is None: i+=1; continue
        entry=L
        target=entry-TARGET_F*ov if up else entry+TARGET_F*ov
        stop  =entry+STOP_F*ov   if up else entry-STOP_F*ov
        ex=None; mk=False
        for j in range(fj+1,min(fj+1+TIME,n)):
            if up:
                if h[j]>=stop: ex=stop; break
                if l[j]<=target: ex=target; mk=True; break
            else:
                if l[j]<=stop: ex=stop; break
                if h[j]>=target: ex=target; mk=True; break
        if ex is None: ex=c[min(fj+TIME,n-1)]
        out.append(((ex-entry)*side + HALF + (HALF if mk else -HALF), t[i])); i=j+1
    return out

if __name__=="__main__":
    import os
    path=os.path.join(os.path.dirname(__file__),"..","reports","xau_m5_3y.csv")
    t,o,c,h,l=load(path); tr=backtest(t,o,c,h,l)
    USD=10.0
    print("SNAP-ICT-MAKER walk-forward (0.10 lot):")
    for y in ("2023","2024","2025","2026"):
        p=np.array([x for x,tt in tr if tt[:4]==y])
        if len(p)<1: print(f"  {y}: no trades"); continue
        gp=p[p>0].sum();gl=-p[p<0].sum();pf=gp/gl if gl>0 else float('inf')
        print(f"  {y}: trades={len(p):4d}  WR={100*(p>0).mean():4.0f}%  PnL=${p.sum()*USD:>+7,.0f}  PF={pf:.2f}")
    allp=np.array([x for x,_ in tr])
    print(f"  ALL: trades={len(allp)}  PnL=${allp.sum()*USD:+,.0f}")
