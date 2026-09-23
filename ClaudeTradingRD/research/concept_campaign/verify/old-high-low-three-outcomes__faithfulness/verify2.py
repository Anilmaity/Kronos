import sys, importlib.util
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05b")
import concept_lab as cl
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05b/old-high-low-three-outcomes.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
m1 = cl.load_m1(); ev = orig.detect(m1)
print(__import__("pandas").Series(cl.to_ny(ev.decision_time).hour).value_counts(normalize=True).sort_index().round(3).to_dict())
for kw in [dict(max_hold="10h", ctrl_tod_tol_min=30), dict(max_hold="150min", ctrl_tod_tol_min=30, n_boot=2000)]:
    r = cl.trade_test(ev, **{"n_boot": 500, **kw})
    print(kw, r["n"], round(r["diff"],4), round(r["ci_lo"],3), round(r["ci_hi"],3), round(r["p"],3), r["verdict"], r["exposure_bars"])
