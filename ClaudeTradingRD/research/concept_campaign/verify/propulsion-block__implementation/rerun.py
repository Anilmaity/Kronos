import os, sys, time
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
import importlib.util
spec = importlib.util.spec_from_file_location("pb", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a/propulsion-block.py")
pb = importlib.util.module_from_spec(spec); spec.loader.exec_module(pb)
cl, np, pd = pb.cl, pb.np, pb.pd
t=time.time()
m1 = cl.load_m1()
ev = detect_b = pb.detect(m1, "body")
print("events", len(ev), time.time()-t, "fp", cl.frame_fingerprint(ev) if hasattr(cl,'frame_fingerprint') else '')
ev.to_pickle("orig_b.pkl")
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
print(pb.summary(res))
res["_trades"].to_pickle("orig_b_trades.pkl")
