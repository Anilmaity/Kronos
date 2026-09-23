import os, sys
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *  # noqa
m1 = cl.load_m1(); here = os.path.dirname(os.path.abspath(__file__))
ev0 = pd.read_pickle(os.path.join(here, "book15.pkl"))[["decision_time","available_at","direction","stop_px","rr"]]
t = ev0["decision_time"]
run = cl.running_hilo(t, "1D", m1=m1); cov = (run["high"]-run["low"]).to_numpy()
adr = asof_ref(daily_ref(m1, 20, 600, 1.0), t)["adr"].to_numpy(float)
ok = np.isfinite(cov) & np.isfinite(adr)
ev = ev0[ok].reset_index(drop=True); ev["g"] = cov[ok] < adr[ok]
r = cl.gate_test(ev, "g", mask_available_at="decision_time", max_hold="150min", claim="+", n_boot=2000, ctrl_tod_tol_min=30, keep_trades=True)
print("TOD-matched ctrl: n", r["n"], "diff %+.4f [%+.4f,%+.4f] p=%.3f %s" % (r["diff"], r["ci_lo"], r["ci_hi"], r["p"], r["verdict"]),
      {k: round(v["diff"],3) for k, v in r["halves"].items() if isinstance(v, dict)}, {k: round(v["diff"],3) for k, v in (r.get("blocks") or {}).items()})
tr = pd.read_pickle(os.path.join(here, "base_trades.pkl"))
tr["x"] = tr["net_R"] - tr["ctrl_mean_R"]; tr["x5"] = tr["net_R_5050"] - tr["ctrl_mean_R_5050"]
g = tr["gate"].astype(bool)
print("stop-first diff %+.4f  50/50 diff %+.4f" % (tr.x[g].mean()-tr.x[~g].mean(), tr.x5[g].mean()-tr.x5[~g].mean()))
ny = cl.to_ny(pd.DatetimeIndex(tr["decision_time"])); tr["h"] = ny.hour; tr["y"] = ny.year
# hour-stratified diff (weights = complement counts)
rows = []
for h, d in tr.groupby("h"):
    a, b = d.x[d.gate.astype(bool)], d.x[~d.gate.astype(bool)]
    if len(b) >= 20: rows.append((h, len(a), len(b), a.mean()-b.mean()))
hs = pd.DataFrame(rows, columns=["h","ng","nc","diff"]); print(hs.round(3).to_string())
print("hour-stratified (complement-weighted) diff %+.4f" % np.average(hs["diff"], weights=hs["nc"]))
print("complement share by NY hour top:", (~g).groupby(tr.h).mean().sort_values(ascending=False).head(6).round(2).to_dict())
yy = tr.groupby("y").apply(lambda d: pd.Series({"nc": (~d.gate.astype(bool)).sum(), "diff": d.x[d.gate.astype(bool)].mean()-d.x[~d.gate.astype(bool)].mean()}))
print(yy.round(3).to_string())
# leave-one-year-out
for y in sorted(tr.y.unique()):
    d = tr[tr.y != y]; gg = d.gate.astype(bool)
    print("drop", y, "%+.4f" % (d.x[gg].mean()-d.x[~gg].mean()), end="; ")
print()
# complement driver: how far over ADR (ratio buckets)
cr = pd.Series(cov[ok]/adr[ok]); 
tr2 = tr.set_index("ev_id") if "ev_id" in tr else tr
