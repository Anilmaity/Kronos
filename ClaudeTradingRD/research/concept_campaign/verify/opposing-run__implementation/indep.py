import sys
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl, numpy as np, pandas as pd
m1=cl.load_m1()
b=cl.bars("4h",grid4h="forex")
rows=[]
idx=m1.index
O=m1.open.to_numpy(); H=m1.high.to_numpy(); L=m1.low.to_numpy(); C=m1.close.to_numpy()
for st,ct in zip(b.index,b.close_time):
    dec=st+pd.Timedelta(minutes=120)
    if dec>=ct: continue
    i0=idx.searchsorted(st); i1=idx.searchsorted(dec)  # bars starting in [st,dec) -> closed by dec
    n=i1-i0
    if n<60: continue
    last=idx[i1-1]
    if dec-(last+pd.Timedelta(minutes=1))>=pd.Timedelta(minutes=30): continue
    o=O[i0]; p=C[i1-1]; hi=H[i0:i1].max(); lo=L[i0:i1].min()
    d=np.sign(p-o)
    if d==0 or hi<=lo: continue
    opp=(o-lo) if d>0 else (hi-o)
    rows.append((dec,int(d),lo if d>0 else hi,opp/(hi-lo)<=0.30, opp/(hi-lo)))
ev=pd.DataFrame(rows,columns=["decision_time","direction","stop_px","shallow","ratio"])
ev["available_at"]=ev.decision_time; ev["rr"]=np.nan
ev.to_pickle("indep_ev.pkl")
print(len(ev),ev.shallow.mean())
old=pd.read_pickle("ev.pkl")
mg=old.merge(ev,on="decision_time",how="outer",suffixes=("_o","_n"),indicator=True)
print(mg._merge.value_counts())
both=mg[mg._merge=="both"]
print("dir mismatch",(both.direction_o!=both.direction_n).sum(),"stop mismatch",(~np.isclose(both.stop_px_o,both.stop_px_n)).sum(),"gate mismatch",(both.shallow_o!=both.shallow_n).sum())
res=cl.gate_test(ev[["decision_time","available_at","direction","stop_px","rr","shallow"]],"shallow",mask_available_at="decision_time",max_hold="120min")
print({k:res.get(k) for k in ("verdict","n","diff","ci_lo","ci_hi","p","mde","ci_components","verdict_detail")})
