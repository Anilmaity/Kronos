import sys, importlib.util
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl, numpy as np, pandas as pd
spec=importlib.util.spec_from_file_location("orun","/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04a/opposing-run.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
ev=mod.detect(cl.load_m1())
print(len(ev), ev.shallow.mean(), cl.frame_fingerprint(ev))
res=cl.gate_test(ev,"shallow",mask_available_at="decision_time",max_hold="120min",keep_trades=True)
print({k:res.get(k) for k in ("verdict","n","diff","ci_lo","ci_hi","p","mde","exposure_bars","ties","ctrl_overlap","ci_components","dependence","control")})
tr=res["_trades"]; print(tr.columns.tolist()); print(tr.head())
tr.to_pickle("trades.pkl"); ev.to_pickle("ev.pkl")
