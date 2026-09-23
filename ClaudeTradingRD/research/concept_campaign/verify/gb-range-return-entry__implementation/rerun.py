import sys, importlib.util, numpy as np, pandas as pd
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl
spec=importlib.util.spec_from_file_location("orig","/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a/gb-range-return-entry.py")
o=importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
m1=cl.load_m1()
ev=o.detect(m1)
print(len(ev), cl.frame_fingerprint(ev))
ev.to_pickle("orig_events.pkl")
res=cl.trade_test(ev,max_hold="24h",ctrl_tod_tol_min=30, keep_trades=True)
for k in ("n","diff","ci_lo","ci_hi","p","verdict","avg_R","win_rate"): print(k,res.get(k))
print(res["halves"]["H1"]["diff"],res["halves"]["H2"]["diff"])
res["_trades"].to_pickle("orig_trades.pkl")
