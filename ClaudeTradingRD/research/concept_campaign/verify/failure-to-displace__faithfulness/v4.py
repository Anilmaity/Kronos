import os, sys
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
tr = pd.read_pickle("trades_a.pkl"); tr["d"]=tr.net_R-tr.ctrl_mean_R
print("pooled d risk>=0.30:", tr.d[tr.risk>=0.3].mean(), "n", (tr.risk>=0.3).sum(), " risk<0.30:", tr.d[tr.risk<0.3].mean())
print("share of total diff sum from risk<0.30:", tr.d[tr.risk<0.3].sum()/tr.d.sum())
import importlib.util
spec = importlib.util.spec_from_file_location("ftd", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a/failure-to-displace.py")
m = importlib.util.module_from_spec(spec); sys.path.insert(0,"/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a"); spec.loader.exec_module(m)
b = cl.build_bars(cl.load_m1(), "15min")
ev = m.ftd(b)
c = b.set_index("close_time")["close"]
cl_at = c.reindex(pd.DatetimeIndex(ev.decision_time)).to_numpy()
sd = np.abs(ev.stop_px.to_numpy() - cl_at)
atr = (b.high-b.low).rolling(96).mean().shift(0); atr.index=b.close_time
a = atr.reindex(pd.DatetimeIndex(ev.decision_time)).to_numpy()
for name, keep in (("stopdist>=0.30$", sd>=0.3), ("stopdist>=0.1*ATR15", sd>=0.1*a)):
    e2 = ev[keep].reset_index(drop=True)
    r = cl.trade_test(e2, max_hold="150min")
    print(name, r['n'], round(r['diff'],4), [round(r['ci_lo'],4), round(r['ci_hi'],4)], r['verdict'], {k: round(v.get('diff') or 0,4) for k,v in r['blocks'].items() if isinstance(v,dict)}, flush=True)
