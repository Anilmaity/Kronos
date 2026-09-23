import sys, runpy, time
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
S = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_02b/poi-density-by-timeframe.py"
mod = runpy.run_path(S, run_name="notmain")
t=time.time()
ev = mod["detect"](cl.load_m1())          # fresh, no cache
print("fresh detect", len(ev), ev.poi_ok.mean(), time.time()-t)
ev.to_pickle("orig_events.pkl")
print("fp", cl.frame_fingerprint(ev))
res = cl.gate_test(ev, "poi_ok", mask_available_at="decision_time", max_hold="10h", keep_trades=True)
print({k: res.get(k) for k in ("n","diff","ci_lo","ci_hi","p","verdict","verdict_detail","events_fp")})
tr = res["_trades"]; tr.to_pickle("orig_trades.pkl"); print(tr.columns.tolist()); print(tr.head())
