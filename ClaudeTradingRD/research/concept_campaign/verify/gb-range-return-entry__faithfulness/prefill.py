import os, sys, numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
D = os.path.dirname(os.path.abspath(__file__))
m1 = cl.load_m1()
t = cl.data.utc_ns(m1.index).view("int64"); H = m1.high.to_numpy(); L = m1.low.to_numpy(); O = m1.open.to_numpy()
ev = pd.read_pickle(os.path.join(D, "ev_base.pkl"))
d = ev.direction.to_numpy(); px = ev.limit_px.to_numpy()
tgt = px + d * ev.target_dist.to_numpy(); A = ev.anchor.to_numpy()
s0 = ev.signal_t.dt.tz_convert("UTC").astype("int64").to_numpy() if hasattr(ev.signal_t, "dt") else None
fill_start = ev.decision_time.astype("int64").to_numpy() - 60_000_000_000
ran = np.zeros(len(ev), bool); thru = np.zeros(len(ev), bool); slip = np.zeros(len(ev))
for i in range(len(ev)):
    a = np.searchsorted(t, s0[i], "left"); z = np.searchsorted(t, fill_start[i], "left")
    hh, ll = H[a:z], L[a:z]
    if d[i] == -1:   # short after bullish flip: target below, anchor below
        ran[i] = (ll <= tgt[i]).any(); thru[i] = (ll < A[i]).any()
    else:
        ran[i] = (hh >= tgt[i]).any(); thru[i] = (hh > A[i]).any()
    k = np.searchsorted(t, ev.decision_time.astype("int64").to_numpy()[i], "left")
    if k < len(O): slip[i] = d[i] * (px[i] - O[k]) / ev.stop_dist.to_numpy()[i]  # + = entry better than limit
print("target traded before fill:", ran.mean().round(3), " anchor traded before fill:", thru.mean().round(3))
print("entry vs limit (R, +=better):", pd.Series(slip).describe().round(3).to_dict())
for lab, keep in [("drop_ran_first", ~ran), ("drop_ran_or_thru", ~(ran | thru)), ("only_ran_first", ran)]:
    e = ev[keep].reset_index(drop=True)
    r = cl.trade_test(e, max_hold="24h", ctrl_tod_tol_min=30)
    print(f"{lab:18s} n={r['n']} diff={r['diff']:+.3f} [{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] p={r['p']:.3f} H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} {r['verdict']}")
# per-year from base trades
r = pd.read_pickle(os.path.join(D, "base_res.pkl")); tr = r["_trades"]
print(tr.columns.tolist()[:30])
