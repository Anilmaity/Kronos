import os; os.environ["CONCEPT_LAB_LEDGER_DISABLE"]="1"
import sys, pandas as pd, numpy as np
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python"); import concept_lab as cl
t=pd.read_parquet('base_trades.parquet'); t['d']=t.net_R-t.ctrl_mean_R; t['d5050']=t.net_R_5050-t.ctrl_mean_R_5050
ev=cl.cache_frame("breaker_15m_ll40_rt20", lambda: None) if False else None
def bs(x, B=2000, seed=1):
    rng=np.random.default_rng(seed); x=np.asarray(x); m=[x[rng.integers(0,len(x),len(x))].mean() for _ in range(B)]; return np.percentile(m,[2.5,97.5]).round(3)
print("all", round(t.d.mean(),4), "5050", round(t.d5050.mean(),4))
day=t.groupby(t.decision_time.dt.date).d.mean()
print("day-cluster ci", bs(t.groupby(t.decision_time.dt.date).d.sum().values*0+0) if False else "")
t['yr']=t.decision_time.dt.year
print(t.groupby('yr').d.agg(['count','mean']).round(3).T.to_string())
print(t.groupby('direction').d.agg(['count','mean']).round(3))
q=t.decision_time.dt.to_period('Q'); qq=t.groupby(q).d.sum().sort_values(ascending=False)
tot=t.d.sum(); print("total sum R diff", round(tot,1), "top4 quarters", qq.head(4).round(1).to_dict(), "share", round(qq.head(4).sum()/tot,2))
yy=t.groupby('yr').d.sum().sort_values(ascending=False); print("top yr share", round(yy.iloc[0]/tot,2), "top2", round(yy.iloc[:2].sum()/tot,2))
for drop in [2021,2022,2023]:
    s=t[t.yr!=drop]; print('drop',drop, round(s.d.mean(),4), bs(s.d))
s=t[~t.yr.isin([2021,2022,2023])]; print('drop 21-23', round(s.d.mean(),4), bs(s.d))
# bias split
import importlib.util
spec=importlib.util.spec_from_file_location("bb","/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_02b/breaker-block.py"); bb=importlib.util.module_from_spec(spec); spec.loader.exec_module(bb)
m1=cl.load_m1(); db=bb.daily_bias(m1); bz=cl.asof(db, pd.DatetimeIndex(t.decision_time))
bias=bz['bias'].fillna(0).to_numpy(); t['al']=np.where(bias==0,'none',np.where(bias==t.direction,'aligned','against'))
print(t.groupby('al').d.agg(['count','mean']).round(3))
for g in ['aligned','against','none']: print(g, bs(t[t.al==g].d))
