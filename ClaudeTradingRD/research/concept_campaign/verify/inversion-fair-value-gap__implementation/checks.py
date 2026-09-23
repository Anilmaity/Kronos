import os, sys
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
m1 = cl.load_m1(); ev = pd.read_parquet("orig_events.parquet")
# own resolver: entry next M1 open >= decision, stop-first ties, 150 min clock, gross R
mt = m1.index.values.astype("datetime64[ns]").astype(np.int64); o,h,l,c = (m1[x].values for x in ("open","high","low","close"))
dt = ev.decision_time.values.astype("datetime64[ns]").astype(np.int64)
R=[]
for t,d,sp in zip(dt, ev.direction.values, ev.stop_px.values):
    a = np.searchsorted(mt, t); 
    if a>=len(mt): continue
    e = o[a]; sd = d*(e-sp)
    if sd<=0: continue
    tp = e + d*2*sd; end = np.searchsorted(mt, mt[a]+150*60_000_000_000)
    r=None
    for q in range(a, end):
        if (d>0 and l[q]<=sp) or (d<0 and h[q]>=sp): r = d*((min(o[q],sp) if d>0 else max(o[q],sp)) - e)/sd if q>a or True else -1; 
        if r is not None: break
        if (d>0 and h[q]>=tp) or (d<0 and l[q]<=tp): r=2.0; break
    if r is None: r = d*(c[end-1]-e)/sd
    R.append(r)
R=np.array(R); print("own gross avg R", len(R), R.mean(), "win", (R>0).mean())
# sensitivity: control holding NY clock fixed (trap 9)
for kw in ({"ctrl_tod_tol_min":30}, {"hold_basis":"bars"}):
    r = cl.trade_test(ev, max_hold="150min", **kw)
    print(kw, {k:r.get(k) for k in ("verdict","diff","ci_lo","ci_hi","p")}, r["halves"]["H1"]["diff"], r["halves"]["H2"]["diff"])
r = cl.trade_test(ev, max_hold="150min", keep_trades=True)
tr = r["_trades"]; print(tr.columns.tolist()[:30])
