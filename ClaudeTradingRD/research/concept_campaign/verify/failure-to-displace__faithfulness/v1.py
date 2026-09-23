import os, sys
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
import importlib.util
spec = importlib.util.spec_from_file_location("ftd", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a/failure-to-displace.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m1 = cl.load_m1()
ev = cl.cache_frame("ftd_15m_v1", lambda: m.detect_a(m1))
def short(tag, r):
    t = r.get("ties", {})
    print(f"{tag:28s} n={r['n']:6d} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] {r['verdict']} H1={r['halves']['H1']['diff']:+.4f} H2={r['halves']['H2']['diff']:+.4f} ov={r.get('ctrl_overlap'):.3f} ties={t.get('real_ambiguous'):.4f}/{t.get('control_ambiguous'):.4f}", flush=True)
    if r.get("blocks"): print("   blocks", {k: round(v.get('diff') or 0,4) for k,v in r['blocks'].items() if isinstance(v, dict)})
r = cl.trade_test(ev, max_hold="150min", keep_trades=True); short("repro", r)
tr = r["_trades"]
tr.to_pickle("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/failure-to-displace__faithfulness/trades_a.pkl")
print(tr.columns.tolist())
d = tr["net_R"] - tr["ctrl_mean_R"]
yr = pd.DatetimeIndex(tr["decision_time"]).year
print("by year:\n", d.groupby(yr).agg(['mean','count']).round(4))
if "net_R_5050" in tr:
    d5 = tr["net_R_5050"] - tr["ctrl_mean_R_5050"]; print("5050 diff", d5.mean())
# post-B1 subset
post = ev[ev.decision_time >= pd.Timestamp("2018-08-22 12:00", tz="UTC")].reset_index(drop=True)
short("post-2018-08-22", cl.trade_test(post, max_hold="150min"))
post19 = ev[ev.decision_time >= pd.Timestamp("2019-01-01", tz="UTC")].reset_index(drop=True)
short("2019+", cl.trade_test(post19, max_hold="150min"))
short("tod30", cl.trade_test(ev, max_hold="150min", ctrl_tod_tol_min=30))
for tf in ("5min", "30min", "1h"):
    e2 = m.ftd(cl.build_bars(m1, tf))
    hold = {"5min":"50min","30min":"300min","1h":"600min"}[tf]
    short(f"tf {tf} hold {hold}", cl.trade_test(e2, max_hold=hold))
