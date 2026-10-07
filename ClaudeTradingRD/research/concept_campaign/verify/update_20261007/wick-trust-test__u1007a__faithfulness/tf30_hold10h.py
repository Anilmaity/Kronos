import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import cl, np, pd, s, wtt
wtt.HTF, wtt.LTF, wtt.HALT_NS = "1D", "30min", pd.Timedelta("30min").value
ev = cl.cache_frame("verify_u1007a_1D_30min_halt30min", lambda: wtt.detect_a(cl.load_m1()))
for h in ("10h",):
    r = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold=h)
    print("1D/30m hold", h, s(r), {k: round(v["diff"], 3) for k, v in r["blocks"].items()})
