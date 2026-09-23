import os, sys, importlib.util, json
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
import numpy as np, pandas as pd
spec = importlib.util.spec_from_file_location("adr", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b/average-daily-range.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ev = m.detect(cl.load_m1())
print(len(ev), cl.frame_fingerprint(ev))
res = cl.gate_test(ev, "open_adr", mask_available_at="decision_time", max_hold="150min", claim="+", keep_trades=True)
for k in ("n","diff","ci_lo","ci_hi","p","verdict","events_fp"): print(k, res.get(k))
print(res["halves"]["H1"]["diff"], res["halves"]["H2"]["diff"])
tr = res["_trades"]; tr.to_pickle("trades.pkl"); ev.to_pickle("ev.pkl")
print(tr.columns.tolist()); print(tr.head())
