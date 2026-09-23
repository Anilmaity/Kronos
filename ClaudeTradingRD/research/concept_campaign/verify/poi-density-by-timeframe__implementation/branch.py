import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import pandas as pd, numpy as np, concept_lab as cl
from detectors.cisd import cisd_events
from detectors.poi import poi_gate
b = cl.build_bars(cl.load_m1(), "1h"); ohlc = b[["open","high","low","close"]]
ev = cisd_events(ohlc, level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
pos = b.index.get_indexer(pd.DatetimeIndex(ev.confirm_time))
out = []
for p, et, dr in zip(pos, ev.extreme_time, ev.direction):
    r = poi_gate(ohlc.iloc[:p+1], et, dr, timeframe="1h", setup_type="reversal")
    out.append((r.passed, r.kinds_required, r.reason, r.detail["last_bar_used"] <= ohlc.index[p]))
d = pd.DataFrame(out, columns=["passed","req","reason","nolook"])
print(d.nolook.all()); print(d.groupby(["reason"]).size())
tr = pd.read_pickle("orig_trades.pkl"); print("entry==decision share", (tr.entry_time==tr.decision_time).mean(), (tr.entry_time>=tr.decision_time).all())
