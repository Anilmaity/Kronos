import sys, importlib.util
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
spec = importlib.util.spec_from_file_location("sons", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_04a/sons-model.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ev = m.detect(cl.load_m1())
print(len(ev), cl.frame_fingerprint(ev))
ev.to_parquet("orig_events.parquet")
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
for k in ("n","avg_R","control","diff","ci_lo","ci_hi","verdict","verdict_detail"):
    print(k, res[k] if k!="control" else res[k]["avg_R"])
print(res["halves"]["H1"]["diff"], res["halves"]["H2"]["diff"])
res["_trades"].to_parquet("orig_trades.parquet")
