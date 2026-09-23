import sys, json, importlib.util
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
spec = importlib.util.spec_from_file_location("po3", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_own_02a/po3-four-hour-opening-times.py")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_own_02a")
po3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(po3)
m1 = cl.load_m1()
K = ("n","avg_R","diff","ci_lo","ci_hi","p","verdict")
def s(tag, r):
    h = r.get("halves") or {}
    print(f"{tag:45s}", {k: (round(r[k],4) if isinstance(r.get(k),float) else r.get(k)) for k in K},
          "H1", round(h.get("H1",{}).get("diff",np.nan),3), "H2", round(h.get("H2",{}).get("diff",np.nan),3),
          "ctrlR", round(r["control"]["avg_R"],3), "exp", {k:round(v,1) if isinstance(v,float) else v for k,v in r["exposure_bars"].items()}, flush=True)
ev = po3.make_detect("futures", 6)(m1)
print("n", len(ev), "long share", (ev.direction==1).mean())
r = cl.trade_test(ev, max_hold="4h", keep_trades=True); s("repro", r)
tr = r["_trades"]; print(tr.columns.tolist())
print({b: round(v["diff"],3) for b,v in r["blocks"].items()})
s("tod30", cl.trade_test(ev, max_hold="4h", ctrl_tod_tol_min=30, n_boot=500))
s("hold bars", cl.trade_test(ev, max_hold="4h", hold_basis="bars", n_boot=500))
s("ex-B1 (>=2018-08-22)", cl.trade_test(ev[ev.decision_time>="2018-08-22"].reset_index(drop=True), max_hold="4h", n_boot=500))
s("2019+", cl.trade_test(ev[ev.decision_time>="2019-01-01"].reset_index(drop=True), max_hold="4h", n_boot=500))
for d in (1,-1):
    s(f"dir {d}", cl.trade_test(ev[ev.direction==d].reset_index(drop=True), max_hold="4h", n_boot=500))
for rr in (1.5, 3.0):
    e2 = ev.copy(); e2["rr"] = rr; s(f"rr {rr}", cl.trade_test(e2, max_hold="4h", n_boot=500))
s("hold 8h", cl.trade_test(ev, max_hold="8h", n_boot=500))
# slot sweep on futures grid (and forex grid) : C2 at slot h -> trade next candle
for grid, hours in (("futures",(2,6,10,22)),("forex",(1,5,9,21))):
    for h in hours:
        e = po3.make_detect(grid, h)(m1)
        s(f"{grid} C2@{h:02d}", cl.trade_test(e, max_hold="4h", n_boot=500))
