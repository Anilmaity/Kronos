"""Independent developing-daily-candle gate (no harness session helpers)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

m1 = cl.load_m1()
ev = pd.read_pickle("orig_events.pkl")
idx = m1.index.tz_convert("UTC")
ny = idx.tz_convert("America/New_York")
# trading day: NY local time shifted +6h -> date (18:00 NY open)
tday = (ny.tz_localize(None) + pd.Timedelta(hours=6)).normalize()
df = pd.DataFrame({"o": m1.open.to_numpy(), "h": m1.high.to_numpy(), "l": m1.low.to_numpy(),
                   "c": m1.close.to_numpy(), "td": tday}, index=idx)
g = df.groupby("td", sort=False)
df["dopen"] = g["o"].transform("first")
df["dhigh"] = g["h"].cummax()
df["dlow"] = g["l"].cummin()
close_t = (idx + pd.Timedelta(minutes=1)).asi8
t = pd.DatetimeIndex(ev.decision_time).tz_convert("UTC")
def state(tt, lag_min=0):
    q = (tt - pd.Timedelta(minutes=lag_min)).asi8
    pos = np.searchsorted(close_t, q, side="right") - 1
    row = df.iloc[pos]
    ttd = (tt.tz_convert("America/New_York").tz_localize(None) + pd.Timedelta(hours=6)).normalize()
    same = (row.td.to_numpy() == ttd.to_numpy()) & (pos >= 0)
    # also require the bar is strictly closed before t
    assert (close_t[pos] <= tt.asi8).all()
    o = np.where(same, row.dopen, np.nan); h = np.where(same, row.dhigh, np.nan)
    l = np.where(same, row.dlow, np.nan); c = np.where(same, row.c, np.nan)
    return o, h, l, c
d = ev.direction.to_numpy()
def gates(o,h,l,c,cut=1.0):
    body = c - o
    aligned = np.sign(body) == d
    opp = np.where(d > 0, o - l, h - o)
    ok = aligned & (np.abs(body) > 0) & (opp <= cut*np.abs(body))
    return aligned, ok
o,h,l,c = state(t)
a, b = gates(o,h,l,c)
print("gate_a mismatch", (a != ev.gate_a.to_numpy()).sum(), "gate_b mismatch", (b != ev.gate_b.to_numpy()).sum(), "firing b", b.mean())
ev2 = ev[["decision_time","available_at","direction","stop_px","rr"]].copy()
ev2["gb"] = b
def run(mask, label):
    e = ev2.copy(); e["gb"] = mask
    r = cl.gate_test(e, "gb", mask_available_at="decision_time", max_hold="150min")
    print(f"{label:30s} n_g={r['n']:6d} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.3f} {r['verdict']} H1={r['halves']['H1']['diff']:+.4f} H2={r['halves']['H2']['diff']:+.4f}")
    return r
run(b, "indep b")
# stale by 1 minute / 15 minutes (strictly earlier info)
for lag in (1, 15):
    o2,h2,l2,c2 = state(t, lag); _, bl = gates(o2,h2,l2,c2); run(bl, f"b with info lag {lag}m")
for cut in (0.5, 0.75, 1.5, 2.0):
    _, bc = gates(o,h,l,c,cut); run(bc, f"b cut {cut}")
# Tod-matched control
e = ev2.copy()
r = cl.gate_test(e, "gb", mask_available_at="decision_time", max_hold="150min", ctrl_tod_tol_min=30)
print("tod30", r["diff"], r["ci_lo"], r["ci_hi"], r["p"], r["verdict"])
