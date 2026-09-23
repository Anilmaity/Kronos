import sys, numpy as np, pandas as pd
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl
m1=cl.load_m1()
b=cl.build_bars(m1,"15min").reset_index()
o,h,l,c=(b[k].to_numpy(float) for k in ("open","high","low","close"))
ct=pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
rng=np.random.default_rng(11)
def run(name, idx, d, **kw):
    ev=pd.DataFrame({"decision_time":ct[idx],"available_at":ct[idx],"direction":d,
                     "stop_px":np.where(d==-1,h[idx],l[idx]),"rr":2.0})
    ev=ev[ev.direction!=0].drop_duplicates("decision_time").reset_index(drop=True)
    r=cl.trade_test(ev,max_hold="150min",n_boot=300,keep_trades=True,**kw)
    t=r['_trades']; t['d']=t.net_R-t.ctrl_mean_R
    t['q']=pd.qcut(t['risk'].rank(method='first'),5,labels=False)
    g=t.groupby('q').agg(risk=('risk','median'),d=('d','mean'))
    print(name,kw,"n",r['n'],"diff %.4f [%.4f,%.4f]"%(r['diff'],r['ci_lo'],r['ci_hi']),r['verdict'],
          "Q:",g.d.round(3).tolist(),"medrisk",g.risk.round(2).tolist(),flush=True)
    return t
N=len(b)
# null A: fade a random 15m candle (short after bullish, long after bearish), stop at its far extreme — cheat-code geometry, no trend
idx=np.sort(rng.choice(np.arange(30,N-1),12000,replace=False))
dA=np.where(c[idx]>o[idx],-1,np.where(c[idx]<o[idx],1,0))
run("A fade-candle no-trend",idx,dA)
# null B: random direction, stop at the just-closed candle's extreme
dB=rng.choice([-1,1],len(idx))
run("B randdir",idx,dB)
# null C: follow the candle (long after bullish, stop at its low)
run("C follow-candle",idx,-dA)
