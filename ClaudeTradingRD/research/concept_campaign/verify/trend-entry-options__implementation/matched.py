import sys, numpy as np, pandas as pd
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl
m1=cl.load_m1()
b=cl.build_bars(m1,"15min").reset_index()
o,h,l,c=(b[k].to_numpy(float) for k in ("open","high","low","close"))
ct=pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
d=np.where(c>o,-1,np.where(c<o,1,0)); idx=np.flatnonzero(d!=0); idx=idx[idx>30]
ev=pd.DataFrame({"decision_time":ct[idx],"available_at":ct[idx],"direction":d[idx],
                 "stop_px":np.where(d[idx]==-1,h[idx],l[idx]),"rr":2.0})
r=cl.trade_test(ev,max_hold="150min",n_boot=200,keep_trades=True)
print("ALL fade-candle n",r['n'],"diff %.4f [%.4f,%.4f]"%(r['diff'],r['ci_lo'],r['ci_hi']),r['verdict'])
t=r['_trades']; t['dd']=t.net_R-t.ctrl_mean_R
oe=pd.read_pickle('orig_events.pkl')
key=set(zip(pd.DatetimeIndex(oe.decision_time).asi8, oe.direction))
t['concept']=[ (a,b_) in key for a,b_ in zip(pd.DatetimeIndex(t.decision_time).asi8,t.direction)]
t['dec']=pd.qcut(t.risk.rank(method='first'),10,labels=False)
g=t.groupby(['dec','concept']).dd.agg(['mean','size']).unstack()
print(g.round(3))
# reweight non-concept to concept's risk-decile mix
w=t[t.concept].dec.value_counts(normalize=True)
nc=t[~t.concept].groupby('dec').dd.mean()
print("concept-in-fade-universe mean dd %.4f n=%d"%(t[t.concept].dd.mean(),t.concept.sum()))
print("non-concept fade, reweighted to concept's stop-size mix: %.4f"%(nc*w).sum())
# bootstrap by day of the difference
t['day']=pd.DatetimeIndex(t.decision_time).floor('D')
rng=np.random.default_rng(1); days=t.day.unique(); diffs=[]
gb={k:v for k,v in t.groupby('day')}
for _ in range(300):
    s=pd.concat([gb[x] for x in rng.choice(days,len(days))])
    w_=s[s.concept].dec.value_counts(normalize=True)
    diffs.append(s[s.concept].dd.mean()-(s[~s.concept].groupby('dec').dd.mean()*w_).sum())
print("concept minus stop-matched fade: %.4f  CI [%.4f, %.4f]"%(np.mean(diffs),*np.percentile(diffs,[2.5,97.5])))
