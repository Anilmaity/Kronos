import os, sys, importlib.util
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
S="/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04a/volume-imbalance.py"
sys.path.insert(0, os.path.dirname(S))
spec=importlib.util.spec_from_file_location("vi", S); vi=importlib.util.module_from_spec(spec); spec.loader.exec_module(vi)
m1 = cl.load_m1()
ev = vi.detect(m1)
print(len(ev), cl.frame_fingerprint(ev))
ev.to_pickle("ev_orig.pkl")
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
print({k: res.get(k) for k in ("verdict","n","diff","ci_lo","ci_hi","p","ties","events_fp")})
print(res["halves"]["H1"]["diff"], res["halves"]["H2"]["diff"])
res["_trades"].to_pickle("trades_orig.pkl")
