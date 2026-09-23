import os, sys, numpy as np, pandas as pd
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prefill.py")).read().split("for lab, keep")[0])
b = cl.build_bars(m1, "15min"); bct = cl.data.utc_ns(b["close_time"]).view("int64"); bc = b.close.to_numpy()
C = m1.close.to_numpy()
thru15 = np.zeros(len(ev), bool); thru1 = np.zeros(len(ev), bool)
dt = ev.decision_time.astype("int64").to_numpy()
for i in range(len(ev)):
    a = np.searchsorted(t, s0[i], "left"); z = np.searchsorted(t, fill_start[i], "left")
    cc = C[a:z]
    thru1[i] = (cc < A[i]).any() if d[i] == -1 else (cc > A[i]).any()
    # 15m bars that CLOSED after the signal and at/before the fill decision
    ba = np.searchsorted(bct, s0[i], "right"); bz = np.searchsorted(bct, dt[i], "right")
    q = bc[ba:bz]
    thru15[i] = (q < A[i]).any() if d[i] == -1 else (q > A[i]).any()
print("M1-close thru:", thru1.mean().round(3), " 15m-close thru:", thru15.mean().round(3))
for lab, keep in [("drop_m1close_thru", ~thru1), ("drop_15mclose_thru", ~thru15)]:
    e = ev[keep].reset_index(drop=True)
    r = cl.trade_test(e, max_hold="24h", ctrl_tod_tol_min=30)
    print(f"{lab:18s} n={r['n']} diff={r['diff']:+.3f} [{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] p={r['p']:.3f} H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} {r['verdict']}")
