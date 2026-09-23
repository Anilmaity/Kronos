import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indep import detect, cl, pd
m1 = cl.load_m1()
cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "gate"]
for kw in (dict(polarity="aligned"), dict(fallback=True, both=False)):
    ev = detect(m1, **kw)
    res = cl.gate_test(ev[cols], "gate", mask_available_at="decision_time", max_hold="10h")
    print(kw, round(ev.gate.mean(),3), {k: res.get(k) for k in ("verdict", "n", "n_complement", "diff", "ci_lo", "ci_hi")})
ev = pd.read_pickle("indep_events.pkl")
# swing-taken component only: among events where a swing exists
