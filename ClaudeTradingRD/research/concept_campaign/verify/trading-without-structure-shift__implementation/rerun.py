import sys, time, importlib.util
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_04b/trading-without-structure-shift.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
t=time.time(); m1 = cl.load_m1(); ev = orig.detect_a(m1); print("detect", time.time()-t, len(ev))
ev.to_parquet("orig_events.parquet")
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
for k in ("n","avg_R","diff","ci_lo","ci_hi","p","verdict","events_fp"): print(k, res.get(k))
tr = res["_trades"]; print(tr.columns.tolist()); print(tr.head())
tr.to_parquet("orig_trades.parquet")
