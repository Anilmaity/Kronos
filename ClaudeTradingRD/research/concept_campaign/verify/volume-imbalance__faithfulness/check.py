import sys, importlib.util
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04a')
import concept_lab as cl, numpy as np, pandas as pd
spec = importlib.util.spec_from_file_location("vi", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04a/volume-imbalance.py")
vi = importlib.util.module_from_spec(spec); spec.loader.exec_module(vi)
m1 = cl.load_m1()
ev = vi.detect(m1)
print("n events", len(ev), "fp", cl.frame_fingerprint(ev))
yr = ev.decision_time.dt.year
print(yr.value_counts().sort_index().to_dict())
# feed discontinuity per year
b = cl.build_bars(m1, "15min")
g = (b.open - b.close.shift()).abs(); rng = (b.high-b.low)
print("median |o-prevc| by year:", g.groupby(b.index.year).median().round(3).to_dict())
print("median 15m range by year:", rng.groupby(b.index.year).median().round(2).to_dict())
a = pd.Series(vi.atr(b, 20), index=b.index)
print("median |o-prevc|/ATR by year:", (g/a).groupby(b.index.year).median().round(3).to_dict())
def show(tag, r):
    print(tag, {k: (round(r[k],4) if isinstance(r.get(k), float) else r.get(k)) for k in ("verdict","n","diff","ci_lo","ci_hi","p")},
          "H1", r["halves"]["H1"].get("diff"), "H2", r["halves"]["H2"].get("diff"), "ties", r["ties"], "ovl", round(r["ctrl_overlap"],4))
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
show("FULL", res)
t = res["_trades"]
print(t.columns.tolist()[:30])
t["d"] = t.net_R - t.ctrl_mean_R; t["d5050"] = t.net_R_5050 - t.ctrl_mean_R_5050
t["y"] = pd.DatetimeIndex(t.decision_time).year
print(t.groupby("y").agg(n=("d","size"), diff=("d","mean"), diff5050=("d5050","mean"), se=("d", lambda x: x.std()/np.sqrt(len(x)))).round(3))
print("overall 50/50 diff", round(t.d5050.mean(),4))
post = ev[ev.decision_time >= pd.Timestamp("2019-01-01", tz="UTC")].reset_index(drop=True)
show("POST2019", cl.trade_test(post, max_hold="150min"))
show("2016-18", cl.trade_test(ev[ev.decision_time < pd.Timestamp("2019-01-01", tz="UTC")].reset_index(drop=True), max_hold="150min"))
show("TOD30", cl.trade_test(ev, max_hold="150min", ctrl_tod_tol_min=30))

vi.MIN_SIZE_ATR = 0.25
ev25 = vi.detect(m1); print("n 0.25ATR", len(ev25), ev25.decision_time.dt.year.value_counts().sort_index().to_dict())
show("FLOOR0.25", cl.trade_test(ev25, max_hold="150min"))
