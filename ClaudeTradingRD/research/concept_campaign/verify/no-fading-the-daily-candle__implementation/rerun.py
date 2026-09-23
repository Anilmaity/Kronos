import sys, importlib.util
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b/no-fading-the-daily-candle.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
cl = orig.cl
ev = orig.detect(cl.load_m1())
ev.to_pickle("orig_events.pkl")
print(len(ev), cl.frame_fingerprint(ev))
for col in ("gate_a","gate_b"):
    r = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold="150min")
    print(col, r["n"], r["diff"], r["ci_lo"], r["ci_hi"], r["p"], r["verdict"], r["halves"]["H1"]["diff"], r["halves"]["H2"]["diff"])
