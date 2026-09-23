import sys, importlib.util
p="/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02b/target-liquidity-and-imbalances.py"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02b")
spec=importlib.util.spec_from_file_location("tli", p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
cl=m.cl
ev = m.detect_b(cl.load_m1())
print(len(ev), cl.frame_fingerprint(ev))
res = m.run(ev, "15min")
for k in ["n","observed_rate","null_rate","diff","ci_lo","ci_hi","verdict","halves"]: print(k, res[k])
ev.to_parquet("ev_b.parquet")
