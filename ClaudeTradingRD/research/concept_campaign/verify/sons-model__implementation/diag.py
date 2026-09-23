import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, ".")
import numpy as np, pandas as pd, concept_lab as cl
from indep import mybars, entry
def show(tag, res):
    print(f"{tag}: n={res['n']} avg_R={res['avg_R']:+.4f} ctrl={res['control']['avg_R']:+.4f} diff={res['diff']:+.4f} "
          f"[{res['ci_lo']:+.4f},{res['ci_hi']:+.4f}] H1={res['halves']['H1']['diff']:+.4f} H2={res['halves']['H2']['diff']:+.4f} {res['verdict']}", flush=True)
ev = pd.read_parquet("orig_events.parquet")
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
tr = res["_trades"]; print(tr.columns.tolist())
m1 = cl.load_m1()
e = m1.open.reindex(ev.decision_time).to_numpy()
# stop distance stats relative to price
sd = np.abs(ev.decision_time.map(lambda x: 0) + 0)  # placeholder
show("orig", res)
show("tod30", cl.trade_test(ev, max_hold="150min", ctrl_tod_tol_min=30))
show("bars", cl.trade_test(ev, max_hold="150min", hold_basis="bars"))
# placebo: identical entry mechanic from random 15m closes, random direction, stop = 3-bar extreme
b = mybars(m1, "15min"); rng = np.random.default_rng(7)
idx = rng.choice(np.arange(3, len(b)), size=40000, replace=False); idx.sort()
mt = m1.index.asi8; mh = m1.high.to_numpy(); ml = m1.low.to_numpy()
rows = []
for r in idx:
    d = 1 if rng.random() < .5 else -1
    stop = b.low.iloc[r-2:r+1].min() if d == 1 else b.high.iloc[r-2:r+1].max()
    t0 = pd.Timestamp(b.ct.iloc[r]).value
    x = entry(t0, d, stop, mt, mh, ml)
    if x is not None: rows.append((x, d, stop))
pl = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px"])
pl["decision_time"] = pd.to_datetime(pl.decision_time, utc=True); pl["available_at"] = pl.decision_time; pl["rr"] = 1.0
pl = pl.drop_duplicates("decision_time").sort_values("decision_time").reset_index(drop=True)
show("placebo_mechanic", cl.trade_test(pl, max_hold="150min"))
