"""Faithfulness/robustness check of advanced-market-structure-labeling reading a. Scratch only; ledger disabled."""
import os, sys, json, importlib.util
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
import numpy as np, pandas as pd
T = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a"
sys.path.insert(0, T); sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
spec = importlib.util.spec_from_file_location("am", T + "/advanced-market-structure-labeling.py")
am = importlib.util.module_from_spec(spec); spec.loader.exec_module(am)
OUT = os.path.dirname(os.path.abspath(__file__))
m1 = cl.load_m1()
ev = am.detect(m1, False)
print("n ev", len(ev), cl.frame_fingerprint(ev))
K = ("n", "diff", "ci_lo", "ci_hi", "p", "verdict")
def show(tag, r):
    print(f"{tag:40s}", {k: (round(r[k], 4) if isinstance(r.get(k), float) else r.get(k)) for k in K}, flush=True)
    return {k: r.get(k) for k in K}
out = {}
base = cl.trade_test(ev, max_hold="50min", keep_trades=True)
out["base"] = show("base", base)
tr = base["_trades"]
# 50/50 tie rescoring + per-year + day-block CI
def dayboot(t, v, nb=2000, seed=1):
    days = pd.DatetimeIndex(t).tz_convert("America/New_York").normalize()
    g = pd.Series(v).groupby(days.values)
    s, c = g.sum().to_numpy(), g.count().to_numpy()
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(s), (nb, len(s)))
    b = s[idx].sum(1) / c[idx].sum(1)
    return float(v.mean()), float(np.quantile(b, .025)), float(np.quantile(b, .975))
ok = np.isfinite(tr.ctrl_mean_R) & np.isfinite(tr.ctrl_mean_R_5050)
d_sf = (tr.net_R - tr.ctrl_mean_R)[ok].to_numpy(); d_55 = (tr.net_R_5050 - tr.ctrl_mean_R_5050)[ok].to_numpy()
t = tr.decision_time[ok]
out["stopfirst_dayboot"] = dayboot(t, d_sf); out["5050_dayboot"] = dayboot(t, d_55)
print("stop-first dayboot", out["stopfirst_dayboot"]); print("5050 dayboot", out["5050_dayboot"])
yr = pd.DatetimeIndex(t).year
py = pd.DataFrame({"y": yr, "d": d_sf}).groupby("y").d.agg(["mean", "count", "sem"])
print(py); out["per_year"] = py.round(4).reset_index().to_dict("records")
# leave-one-year-out
out["loyo"] = {int(y): float(d_sf[yr != y].mean()) for y in np.unique(yr)}
print("LOYO", out["loyo"])
# direction split
for dname, s in (("short", -1), ("long", 1)):
    m = (tr.direction[ok] == s).to_numpy(); out[f"dir_{dname}"] = dayboot(t[m], d_sf[m]); print(dname, out[f"dir_{dname}"])
# robustness variants
for tag, kw in (("tod30", dict(ctrl_tod_tol_min=30)), ("bars", dict(hold_basis="bars")),
                ("grid_m1", dict(ctrl_grid="m1")), ("cost0", dict(cost=0.0))):
    out[tag] = show(tag, cl.trade_test(ev, max_hold="50min", **kw))
for h in ("25min", "100min", "150min"):
    out["hold" + h] = show("hold " + h, cl.trade_test(ev, max_hold=h))
for rr in (1.0, 1.5, 3.0):
    e2 = ev.copy(); e2["rr"] = rr; out[f"rr{rr}"] = show(f"rr {rr}", cl.trade_test(e2, max_hold="50min"))
# entry one minute later (robustness to the exact confirmation-close timing)
e3 = ev.copy(); e3["decision_time"] = e3.decision_time + pd.Timedelta("1min")
out["delay1m"] = show("delay +1m", cl.trade_test(e3, max_hold="50min"))
e4 = ev.copy(); e4["decision_time"] = e4.decision_time + pd.Timedelta("5min")
out["delay5m"] = show("delay +5m", cl.trade_test(e4, max_hold="50min"))
# other LTFs listed in yaml (1m, 1H) and 15m
for tf, hold in (("1min", "10min"), ("15min", "150min"), ("1h", "10h")):
    am.TF = tf
    e5 = am.detect(m1, False)
    out["tf" + tf] = show(f"tf {tf} hold {hold}", cl.trade_test(e5, max_hold=hold))
am.TF = "5min"
json.dump(out, open(OUT + "/out.json", "w"), indent=1, default=str)
