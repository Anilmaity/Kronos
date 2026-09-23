import os, sys, time, json
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import importlib.util
spec = importlib.util.spec_from_file_location("am", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a/advanced-market-structure-labeling.py")
am = importlib.util.module_from_spec(spec); spec.loader.exec_module(am)
import concept_lab as cl
ev = am.detect(cl.load_m1(), False); print(len(ev), cl.frame_fingerprint(ev))
ev.to_pickle("ev_orig.pkl")
res = cl.trade_test(ev, max_hold="50min", keep_trades=True)
res["_trades"].to_pickle("trades_orig.pkl")
print({k: res.get(k) for k in ("n","diff","ci_lo","ci_hi","p","verdict","verdict_detail","events_fp","ci_components")})
