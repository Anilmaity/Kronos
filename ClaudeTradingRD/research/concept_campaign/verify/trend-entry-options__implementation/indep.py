"""Independent re-implementation of trend-entry-options + geometry-matched nulls."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl
m1=cl.load_m1()
b=cl.build_bars(m1,"15min").reset_index()
o,h,l,c=(b[k].to_numpy(float) for k in ("open","high","low","close"))
ct=pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
n=len(b)
# ATR(20) of true range, known at close of i
tr=np.maximum(h-l, np.maximum(abs(h-np.r_[c[0],c[:-1]]), abs(l-np.r_[c[0],c[:-1]])))
atr=pd.Series(tr).rolling(20).mean().to_numpy()
atr_prev=np.r_[np.nan,atr[:-1]]
# fractal 2/2 swings: swing at p confirmed at close of p+2
sh=np.zeros(n,bool); sl=np.zeros(n,bool)
for p in range(2,n-2):
    sh[p]= h[p]>max(h[p-2],h[p-1]) and h[p]>=max(h[p+1],h[p+2])
    sl[p]= l[p]<min(l[p-2],l[p-1]) and l[p]<=min(l[p+1],l[p+2])
MODE=sys.argv[1] if len(sys.argv)>1 else "concept"
TREND=24
rows=[]
lsh=lsl=np.nan; lsh_p=lsl_p=-1
trend=None  # dict(d, start_px, t0, taken)
rng=np.random.default_rng(7)
for i in range(n):
    p=i-2
    if p>=2:
        if sh[p]: lsh,lsh_p=h[p],p
        if sl[p]: lsl,lsl_p=l[p],p
    # evaluate entries on bar i under the trend in force BEFORE bar i's displacement check
    if trend is not None:
        d=trend['d']
        if i-trend['t0']>TREND or (d==1 and c[i]<trend['origin']) or (d==-1 and c[i]>trend['origin']):
            trend=None
    if trend is not None and not trend['taken']:
        d=trend['d']
        ent=None
        if MODE in ("concept","flip"):
            if d==-1 and h[i]>trend['sw'] and c[i]<trend['sw']: ent=(-1,h[i],1)
            elif d==1 and l[i]<trend['sw'] and c[i]>trend['sw']: ent=(1,l[i],1)
            elif (d==-1 and c[i]>o[i]) or (d==1 and c[i]<o[i]): ent=(d,h[i] if d==-1 else l[i],3)
            if ent and MODE=="flip":
                dd=-ent[0]; ent=(dd, h[i] if dd==-1 else l[i], ent[2])
        elif MODE=="withcandle":   # first bar of the trend, whatever its colour, stop at far extreme
            ent=(d,h[i] if d==-1 else l[i],0)
        elif MODE=="nonopp":       # first WITH-trend candle instead of opposing
            if (d==-1 and c[i]<o[i]) or (d==1 and c[i]>o[i]): ent=(d,h[i] if d==-1 else l[i],0)
        if ent:
            rows.append((ct[i],ent[0],ent[1],ent[2],c[i]))
            trend['taken']=True
    # new displacement: close beyond latest swing with bar range >= 1.5 ATR (ATR known at i-1)
    if np.isfinite(atr_prev[i]) and (h[i]-l[i])>=1.5*atr_prev[i]:
        if np.isfinite(lsh) and c[i]>lsh and c[i-1]<=lsh:
            org=l[lsh_p:i+1].min()
            trend=dict(d=1,origin=org,t0=i,taken=False,sw=lsl)
        elif np.isfinite(lsl) and c[i]<lsl and c[i-1]>=lsl:
            org=h[lsl_p:i+1].max()
            trend=dict(d=-1,origin=org,t0=i,taken=False,sw=lsh)
ev=pd.DataFrame(rows,columns=["decision_time","direction","stop_px","opt","close"])
if MODE=="randdir":
    pass
ev["available_at"]=ev["decision_time"]; ev["rr"]=2.0
print(MODE,len(ev),ev.opt.value_counts().to_dict())
res=cl.trade_test(ev[["decision_time","available_at","direction","stop_px","rr"]],max_hold="150min",n_boot=500,keep_trades=True)
for k in ["n","avg_R","diff","ci_lo","ci_hi","verdict","dropped"]: print(" ",k,res.get(k))
t=res['_trades']; t['sd']=t['risk']
t['q']=pd.qcut(t['risk'].rank(method='first'),5,labels=False)
t['d']=t.net_R-t.ctrl_mean_R
print(t.groupby('q').agg(risk=('risk','median'),d=('d','mean'),n=('d','size')).round(3))
t.to_pickle(f'indep_{MODE}.pkl')
