import os, sys, time, json
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_02b")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import importlib.util
spec = importlib.util.spec_from_file_location("bb", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_02b/breaker-block.py")
bb = importlib.util.module_from_spec(spec); spec.loader.exec_module(bb)
import concept_lab as cl
t=time.time()
ev = bb.detect(cl.load_m1()); print("detect s", time.time()-t, len(ev), cl.frame_fingerprint(ev))
ev.to_pickle("ev_orig.pkl")
res = cl.trade_test(ev, max_hold="5h", ctrl_tod_tol_min=30, keep_trades=True)
res["_trades"].to_pickle("trades_orig.pkl")
print({k: res.get(k) for k in ("n","diff","ci_lo","ci_hi","p","verdict","events_fp","ties","exposure_bars")})
