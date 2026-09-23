import sys, importlib.util, time
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd
p="/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05b/balanced-price-range-overlap.py"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05b")
spec=importlib.util.spec_from_file_location("orig", p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ev = m.detect(cl.load_m1())
print(len(ev), cl.frame_fingerprint(ev))
ev.to_parquet("orig_events.parquet")
res = cl.trade_test(ev, max_hold="150min", cluster="bpr_id")
m.show(res); print(res.get("halves"))
