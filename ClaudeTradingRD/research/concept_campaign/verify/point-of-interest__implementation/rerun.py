"""Re-run the original detector + gate_test (no write_result), ledger redirected to scratch."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(HERE, "verify_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
import importlib.util
spec = importlib.util.spec_from_file_location("poi_orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b/point-of-interest.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
cl, pd = m.cl, m.pd
ev = m.detect(cl.load_m1())
ev.to_pickle(os.path.join(HERE, "orig_events.pkl"))
print(len(ev), ev.poi_a.mean(), ev.poi_b.mean(), cl.frame_fingerprint(ev))
res = cl.gate_test(ev, "poi_a", mask_available_at="decision_time", max_hold="10h")
print({k: res.get(k) for k in ("verdict","verdict_detail","n","n_complement","diff","ci_lo","ci_hi","p","events_fp")})
print(res["halves"]["H1"]["diff"], res["halves"]["H2"]["diff"])
