import sys, os
os.environ["CONCEPT_LAB_LEDGER_DISABLE"]="1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
import importlib.util
spec=importlib.util.spec_from_file_location("ftd","/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a/failure-to-displace.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
cl=m.cl; import numpy as np, pandas as pd
m1=cl.load_m1()
ev=m.detect_a(m1)
print(len(ev), ev.head())
res=cl.trade_test(ev, max_hold="150min", keep_trades=True)
print(m.summary(res))
tr=res["_trades"]; tr.to_pickle("trades_a.pkl"); ev.to_pickle("ev_a.pkl")
print(tr.columns.tolist()); print(tr.head())
