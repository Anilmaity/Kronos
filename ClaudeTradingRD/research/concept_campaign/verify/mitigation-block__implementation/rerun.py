import sys, importlib.util
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b")
spec = importlib.util.spec_from_file_location("mb", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b/mitigation-block.py")
mb = importlib.util.module_from_spec(spec); spec.loader.exec_module(mb)
cl = mb.cl
m1 = cl.load_m1()
ev = mb.detect_a(m1)
print("events", len(ev), cl.frame_fingerprint(ev))
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
for k in ["n","avg_R","diff","ci_lo","ci_hi","p","verdict","dropped"]: print(k, res[k])
ev.to_parquet("ev_a.parquet")
res["_trades"].to_parquet("trades_a.parquet")
# dropped: entry beyond stop
mkt = cl.get_market()
i0 = np.searchsorted(mkt.tn, cl.engine.utc_ns(pd.DatetimeIndex(ev.decision_time)), side="left") if hasattr(cl,'engine') else None
