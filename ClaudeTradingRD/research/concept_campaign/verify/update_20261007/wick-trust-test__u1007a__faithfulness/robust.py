import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import cl, np, pd, events, s

ev = events()
G = dict(mask_available_at="decision_time")
out = {}
def run(name, frame=ev, **kw):
    kw = {"max_hold": "10h", **kw}
    r = cl.gate_test(frame, "trusted", **G, **kw)
    out[name] = s(r); print(name, out[name], {k: round(v["diff"], 3) for k, v in r["blocks"].items()},
                           "H1", round(r["halves"]["H1"]["diff"], 3), "H2", round(r["halves"]["H2"]["diff"], 3), flush=True)
    return r

base = run("base")
run("tod30", ctrl_tod_tol_min=30)
for c in (0.25, 0.35):
    r = run(f"spread{c}", cost=c)
    print("   gated book net avg_R", round(r["avg_R"], 4), "complement net", round(r["complement"]["avg_R"], 4))
for h in ("8h", "12h"):
    run(f"hold{h}", max_hold=h)
# hold to the daily candle close (source: "hold towards the close of it")
hb = cl.bars("1D"); hst = hb.index; hct = pd.DatetimeIndex(hb["close_time"])
k = np.searchsorted(hst.asi8, pd.DatetimeIndex(ev.decision_time).asi8 - 1, "right") - 1
e2 = ev.copy(); e2["max_hold"] = (hct[k] - pd.DatetimeIndex(ev.decision_time)).to_numpy()
run("hold_to_daily_close", e2, max_hold=None)
run("rr3", ev.assign(rr=3.0))
# feed-regression exclusion 2019-02 .. 2020-02 (XAUUSD Data Inventory)
t = pd.DatetimeIndex(ev.decision_time)
run("excl_feed_regression", ev[~((t >= "2019-02-01") & (t < "2020-03-01"))].reset_index(drop=True))
# remove the 22:00-01:00 NY cluster entirely
hr = cl.to_ny(t).hour
run("excl_22_01NY", ev[~np.isin(hr, [22, 23, 0, 1])].reset_index(drop=True))
run("only_22_01NY", ev[np.isin(hr, [22, 23, 0, 1])].reset_index(drop=True))

# per-year from the base trade book
b = cl.gate_test(ev, "trusted", **G, max_hold="10h", keep_trades=True)["_trades"]
b["adj"] = b.net_R - b.ctrl_mean_R; b["yr"] = pd.DatetimeIndex(b.decision_time).year
py = b.groupby(["yr", "gate"]).adj.agg(["mean", "size"]).unstack()
py["diff"] = py[("mean", True)] - py[("mean", False)]
print(py.round(3).to_string())
print("years with diff>0:", int((py["diff"] > 0).sum()), "of", len(py))
