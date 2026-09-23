"""Is the ITH labelling doing anything beyond a plain 3-bar fractal? Ledger disabled."""
import os, sys, importlib.util
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
import numpy as np, pandas as pd
T = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a"
sys.path.insert(0, T); sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
from _common import swings3
m1 = cl.load_m1()
K = ("n", "diff", "ci_lo", "ci_hi", "p", "verdict")
def sth_events(tf, mode):
    b = cl.build_bars(m1, tf); h, l = b.high.to_numpy(float), b.low.to_numpy(float)
    sh, sl = swings3(b); ct = b.close_time.to_numpy(); rows = []
    for bull in (False, True):
        x = -l if bull else h; pts = np.flatnonzero(sl if bull else sh)
        for k in range(1, len(pts) - 1):
            p0, p1, p2 = pts[k-1], pts[k], pts[k+1]
            if mode == "sth":       # plain STH: decide at close of bar p1+1, stop at STH
                conf, piv = p1 + 1, p1
            elif mode == "sth_failure":   # ITH-shaped timing but the middle STH is a LOWER high than its left (failure swing)
                if not (x[p0] > x[p1] > x[p2]): continue
                conf, piv = p2 + 1, p1
            elif mode == "right_sth_stop":  # ITH but stop at the right-hand STH (tight alternative he mentions)
                if not (x[p0] < x[p1] > x[p2]): continue
                conf, piv = p2 + 1, p2
            if conf >= len(b): continue
            if x[piv + 1:conf + 1].max(initial=-np.inf) >= x[piv]: continue
            rows.append((ct[conf], 1 if bull else -1, -x[piv] if bull else x[piv]))
    r = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px"])
    r["decision_time"] = pd.DatetimeIndex(r.decision_time).tz_localize("UTC") if pd.DatetimeIndex(r.decision_time).tz is None else pd.DatetimeIndex(r.decision_time)
    r["available_at"] = r.decision_time; r["rr"] = 2.0
    return r.sort_values(["decision_time", "direction"]).reset_index(drop=True)
for tf, hold in (("5min", "50min"), ("1min", "10min")):
    for mode in ("sth", "sth_failure", "right_sth_stop"):
        r = cl.trade_test(sth_events(tf, mode), max_hold=hold)
        print(tf, mode, {k: (round(r[k], 4) if isinstance(r.get(k), float) else r.get(k)) for k in K}, r["halves"]["H1"]["diff"], r["halves"]["H2"]["diff"], flush=True)
