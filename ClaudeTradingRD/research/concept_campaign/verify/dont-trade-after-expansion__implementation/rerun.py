import sys, importlib.util, numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_02b/dont-trade-after-expansion.py")
orig = importlib.util.module_from_spec(spec); sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_02b"); spec.loader.exec_module(orig)
m1 = cl.load_m1()
ev = orig.detect_b(m1)
ev.to_parquet("ev_orig.parquet")
print(len(ev), ev.late_expanded.mean(), cl.frame_fingerprint(ev))
res = cl.gate_test(ev, "late_expanded", mask_available_at="decision_time", max_hold="50min", claim="-")
print({k: res.get(k) for k in ("n","diff","ci_lo","ci_hi","p","verdict","verdict_detail")})
