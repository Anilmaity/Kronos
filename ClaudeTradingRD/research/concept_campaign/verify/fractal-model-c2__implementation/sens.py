import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
a = pd.read_pickle("allc2_orig.pkl")
ev = a[a.conf & a.posok][COLS].reset_index(drop=True)
def run(name, e, **kw):
    kw.setdefault("hold_basis", "bars")
    r = cl.trade_test(e, max_hold="240min", **kw)
    print(f"{name:40s} n={r['n']} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.3f} H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} {r['verdict']} avgR={r['avg_R']:+.3f} ctrl={r['control']['avg_R']:+.3f}", flush=True)
    return r
r0 = run("original", ev, keep_trades=True)
r0["_trades"].to_pickle("trades_orig.pkl")
run("tod_tol30", ev, ctrl_tod_tol_min=30)
run("clock hold", ev, hold_basis="clock")
run("ctrl_grid 4h? (1h)", ev, ctrl_grid="1h")
run("ctrl_grid m1", ev, ctrl_grid="m1")
ny = cl.to_ny(pd.DatetimeIndex(ev.decision_time))
nofri = ~((ny.dayofweek == 4) & (ny.hour >= 16))
run("drop Friday-close C2s", ev[nofri].reset_index(drop=True))
# all C2 without CISD gate
evall = a[a.posok][COLS].reset_index(drop=True)
run("all C2 (no CISD gate)", evall)
evno = a[(~a.conf) & a.posok][COLS].reset_index(drop=True)
run("C2 failing CISD gate", evno)
