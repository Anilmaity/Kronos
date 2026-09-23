import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import pandas as pd, numpy as np
import concept_lab as cl
ev = pd.read_parquet("ev_orig_b.parquet")
def s(tag, r): print(tag, r["verdict"], round(r["diff"],4), [round(r["ci_lo"],4), round(r["ci_hi"],4)], round(r["p"],4), "H", round(r["halves"]["H1"]["diff"],3), round(r["halves"]["H2"]["diff"],3), "real", round(r["avg_R"],4), "ctrl", round(r["control"]["avg_R"],4))
s("tod30", cl.trade_test(ev, max_hold="10h", ctrl_tod_tol_min=30))
s("bars", cl.trade_test(ev, max_hold="600min", hold_basis="bars"))
for d in (1, 2, 5, 15):
    e = ev.copy(); e["decision_time"] += pd.Timedelta(minutes=d); e["available_at"] = e["decision_time"]
    s(f"delay{d}", cl.trade_test(e, max_hold="10h"))
for dr in (1, -1):
    s(f"dir{dr}", cl.trade_test(ev[ev.direction==dr].reset_index(drop=True), max_hold="10h"))
r = cl.trade_test(ev, max_hold="10h", keep_trades=True)
tr = r["_trades"]; print(tr.columns.tolist()); print(tr.head())
