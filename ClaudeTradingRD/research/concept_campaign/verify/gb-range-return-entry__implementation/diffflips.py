import sys, numpy as np, pandas as pd
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a')
sys.path.insert(0,'.')
from common01a import cl, bars_arr, structure_flips
import indep
m1=cl.load_m1(); b=cl.build_bars(m1,"15min")
fo=structure_flips(bars_arr(b),2,2)
fi=pd.DataFrame(indep.flips(b),columns=["bar","dir","anchor_bar","anchor","opp0"])
print(len(fo),len(fi))
mm=fo.merge(fi,on=["bar","dir"],how="outer",indicator=True,suffixes=("_o","_i"))
print(mm._merge.value_counts())
both=mm[mm._merge=="both"]; print("anchor mismatch",(both.anchor_o!=both.anchor_i).sum(),"opp mismatch",(both.opp0_o!=both.opp0_i).sum())
eo=pd.read_pickle("orig_events.pkl"); ei=pd.read_pickle("indep_00.pkl")
x=eo[["decision_time","direction"]].merge(ei[["decision_time","direction","stop_dist"]],how="outer",indicator=True)
print(x._merge.value_counts()); print(x[x._merge!="both"].head(10))
