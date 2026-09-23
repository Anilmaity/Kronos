import sys, importlib.util, numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
D="/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_04b"
sys.path.insert(0, D)
import concept_lab as cl
spec=importlib.util.spec_from_file_location("ir", D+"/intraday-reversal.py"); ir=importlib.util.module_from_spec(spec); spec.loader.exec_module(ir)
from _helpers import day_end_bars, matched_touch_null
m1=cl.load_m1()
ev=ir.detect(m1)
print(len(ev), cl.frame_fingerprint(ev))
ev.to_pickle("orig_events.pkl")
t=pd.DatetimeIndex(ev.decision_time); hb=day_end_bars(m1.index,t)
mkt=cl.get_market(); px=mkt.o[np.minimum(mkt.pos_at_or_after(t),len(mkt.o)-1)]
lvl=ev.level.to_numpy(); side=np.where(ev.direction>0,"below","above")
obs=np.zeros(len(ev),bool)
for sd in ("above","below"):
    m=side==sd; obs[m]=~cl.touch(t[m],lvl[m],sd,horizon_bars=hb[m])["hit"].to_numpy()
nf=matched_touch_null(t,lvl-px,side,hb,tod_tol_min=30,invert=True)
mat=np.column_stack([nf(None,k) for k in range(5)])
print("obs",obs.mean(),"null",np.nanmean(np.nanmean(mat,1)))
pd.DataFrame({"t":t,"obs":obs,"hb":hb,"px":px,"lvl":lvl,"dir":ev.direction.values,**{f"n{k}":mat[:,k] for k in range(5)}}).to_pickle("orig_outcomes.pkl")
