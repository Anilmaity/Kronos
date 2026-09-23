import sys, importlib.util
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02b")
spec = importlib.util.spec_from_file_location("ob", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02b/order-block.py")
ob = importlib.util.module_from_spec(spec); spec.loader.exec_module(ob)
cl = ob.cl
detect = ob.make_detect("b")
ev = detect(cl.load_m1())
print(len(ev), cl.frame_fingerprint(ev) if hasattr(cl,'frame_fingerprint') else '')
ev.to_parquet("ev_orig_b.parquet")
res = cl.trade_test(ev, max_hold="10h")
print({k: res.get(k) for k in ("verdict","n","diff","ci_lo","ci_hi","p","events_fp")})
