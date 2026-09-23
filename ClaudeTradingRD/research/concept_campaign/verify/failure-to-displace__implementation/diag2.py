import sys; sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl, pandas as pd, numpy as np
pd.set_option("display.width",250); pd.set_option("display.max_columns",20)
tr=pd.read_pickle("trades_a.pkl"); tr["d"]=tr.net_R-tr.ctrl_mean_R
m1=cl.load_m1(); print(m1.columns.tolist())
for i in [22467,11854,9641]:
    r=tr.loc[i]; print(r[["decision_time","entry_time","direction","entry","stop","target","risk","exit_time","exit_px","reason","gross_R"]].to_dict())
    t=pd.Timestamp(r.decision_time)
    print(m1.loc[t-pd.Timedelta("4min"):t+pd.Timedelta("3min")])
# price granularity
p=m1.close.to_numpy()[:200000]; print("decimals sample", np.unique(np.round((p*1000)%10)).size)
for lo in [0.05,0.1,0.2,0.3,0.5]:
    s=tr[tr.risk>=lo]; print(lo,len(s), s.d.mean(), "H1",s[pd.DatetimeIndex(s.decision_time).year<2021].d.mean(),"H2",s[pd.DatetimeIndex(s.decision_time).year>=2021].d.mean())
