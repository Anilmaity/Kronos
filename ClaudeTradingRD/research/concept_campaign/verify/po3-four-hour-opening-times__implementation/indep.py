"""Independent implementation from the YAML: straight from M1 in NY time, no build_bars."""
import os, sys
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
m1 = cl.load_m1()
idx = pd.DatetimeIndex(m1.index)
ny = idx.tz_convert("America/New_York")
d = pd.DataFrame({"o": m1["open"].to_numpy(), "h": m1["high"].to_numpy(), "l": m1["low"].to_numpy(),
                  "c": m1["close"].to_numpy(), "date": ny.normalize().tz_localize(None), "hr": ny.hour}, index=idx)
def win(h0):
    w = d[(d.hr >= h0) & (d.hr < h0 + 4)]
    g = w.groupby("date")
    return pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last(), "n": g.o.size()})
p, c = win(2), win(6)
j = p.join(c, lsuffix="_p", rsuffix="_c", how="inner")
bull = (j.l_c < j.l_p) & (j.c_c > j.l_p)
bear = (j.h_c > j.h_p) & (j.c_c < j.h_p)
j = j[bull ^ bear].copy()
j["dir"] = np.where(bull[bull ^ bear], 1, -1)
j["stop"] = np.where(j.dir == 1, j.l_c, j.h_c)
dt = [pd.Timestamp(x).tz_localize("America/New_York") + pd.Timedelta(hours=10) for x in j.index]
j["decision_time"] = pd.DatetimeIndex(dt).tz_convert("UTC")
print("indep events", len(j), "long share", (j.dir == 1).mean())
orig = pd.read_pickle("orig_events.pkl")
a = set(orig.decision_time); b = set(j.decision_time)
print("only orig", len(a - b), "only indep", len(b - a))
print(sorted(a - b)[:5], sorted(b - a)[:5])
mrg = orig.merge(j.reset_index(), on="decision_time")
print("dir mismatch", (mrg.direction != mrg.dir).sum(), "stop max abs diff", (mrg.stop_px - mrg.stop).abs().max())

# own simulator
H, L, O, C = d.h.to_numpy(), d.l.to_numpy(), d.o.to_numpy(), d.c.to_numpy()
tix = idx.values
R = []; ex = []
for t, dr, sp in zip(j.decision_time, j.dir, j.stop):
    i0 = np.searchsorted(tix, t.to_datetime64())
    if i0 >= len(tix): continue
    ent = O[i0]; risk = (ent - sp) * dr
    if risk <= 0: R.append(np.nan); continue
    tp = ent + dr * 2 * risk
    i1 = np.searchsorted(tix, (t + pd.Timedelta("4h")).to_datetime64())
    r = None
    for k in range(i0, i1):
        if dr == 1:
            if L[k] <= sp: r = (min(O[k], sp) - ent) / risk if k > i0 else (min(O[k], sp) - ent) / risk; kind = "stop"; break
            if H[k] >= tp: r = 2.0; kind = "tgt"; break
        else:
            if H[k] >= sp: r = (ent - max(O[k], sp)) / risk; kind = "stop"; break
            if L[k] <= tp: r = 2.0; kind = "tgt"; break
    if r is None:
        r = (C[i1 - 1] - ent) * dr / risk; kind = "time"
    R.append(r); ex.append(kind)
R = np.array(R)
print("own sim n", np.isfinite(R).sum(), "gross avgR", np.nanmean(R), "net", np.nanmean(R) - 0.04,
      "win", np.nanmean(R > 0), pd.Series(ex).value_counts(normalize=True).round(3).to_dict())
yrs = pd.DatetimeIndex(j.decision_time).year
print(pd.Series(R, index=yrs).groupby(level=0).agg(["mean", "size"]).round(3))
ev = pd.DataFrame({"decision_time": j.decision_time.values, "available_at": j.decision_time.values,
                   "direction": j.dir.values, "stop_px": j.stop.values.astype(float), "rr": 2.0})
ev["decision_time"] = pd.DatetimeIndex(ev.decision_time).tz_localize("UTC") if pd.DatetimeIndex(ev.decision_time).tz is None else ev.decision_time
ev["available_at"] = ev["decision_time"]
res = cl.trade_test(ev.reset_index(drop=True), max_hold="4h")
print("INDEP harness:", res["n"], res["avg_R"], res["diff"], res["ci_lo"], res["ci_hi"], res["p"], res["verdict"],
      {h: round(v["diff"], 4) for h, v in res["halves"].items() if isinstance(v, dict)})
res2 = cl.trade_test(ev.reset_index(drop=True), max_hold="4h", ctrl_tod_tol_min=30)
print("TOD-matched control:", res2["n"], res2["control"]["avg_R"], res2["diff"], res2["ci_lo"], res2["ci_hi"], res2["p"], res2["verdict"],
      {h: round(v["diff"], 4) for h, v in res2["halves"].items() if isinstance(v, dict)})
res3 = cl.trade_test(ev.reset_index(drop=True), max_hold="4h", hold_basis="bars")
print("bars hold:", res3["diff"], res3["ci_lo"], res3["ci_hi"], res3["verdict"])
# flipped direction (does sign matter?) with TOD control
evf = ev.copy(); evf["direction"] = -evf.direction
evf["stop_px"] = np.nan
