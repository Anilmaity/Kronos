import os, sys, importlib.util
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04a")
spec = importlib.util.spec_from_file_location("ifvg", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04a/inversion-fair-value-gap.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
cl = mod.cl
ev = mod.detect_b(cl.load_m1())
ev.to_parquet("orig_events.parquet")
print(len(ev), cl.frame_fingerprint(ev))
res = cl.trade_test(ev, max_hold="150min")
print({k: res.get(k) for k in ("verdict","n","diff","ci_lo","ci_hi","p","ties","exposure_bars","ctrl_overlap")})
