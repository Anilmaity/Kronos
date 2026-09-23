import sys, importlib.util
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05b")
import concept_lab as cl
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05b/old-high-low-three-outcomes.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ev = m.detect(cl.load_m1())
print(len(ev), ev.branch.value_counts().to_dict(), cl.frame_fingerprint(ev))
ev.to_pickle("orig_events.pkl")
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
for k in ("n","avg_R","diff","ci_lo","ci_hi","p","verdict","halves"): print(k, res[k] if k!="halves" else {h:(v['n'],round(v['diff'],4)) for h,v in res[k].items() if isinstance(v,dict)})
tr = res["_trades"]; print(tr.columns.tolist()[:30]); tr.to_pickle("orig_trades.pkl")
