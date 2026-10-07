import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import cl, np, pd, s, wtt

def ev_for(htf, ltf, halt):
    wtt.HTF, wtt.LTF, wtt.HALT_NS = htf, ltf, pd.Timedelta(halt).value
    return cl.cache_frame(f"verify_u1007a_{htf}_{ltf}_halt{halt}", lambda: wtt.detect_a(cl.load_m1()))

for htf, ltf, halt, hold in (("1D", "30min", "30min", "5h"), ("4h", "15min", "15min", "150min")):
    ev = ev_for(htf, ltf, halt)
    r = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold=hold)
    print(htf, ltf, "rows", len(ev), "yes", int(ev.trusted.sum()), s(r),
          {k: round(v["diff"], 3) for k, v in r["blocks"].items()}, flush=True)

# reopen-gap check on the base 1D/1h frame: was the confirmed extreme set in the 18:00 NY reopen bar?
ev = ev_for("1D", "1h", "1h")
h1 = cl.bars("1h"); d1 = cl.bars("1D")
hs, hlo, hhi = h1.index.asi8, h1["low"].to_numpy(), h1["high"].to_numpy()
ds = d1.index.asi8
y = ev[ev.trusted].reset_index(drop=True)
dt = pd.DatetimeIndex(y.decision_time).asi8
k = np.searchsorted(ds, dt - 1, "right") - 1
first = np.zeros(len(y), bool)
for i in range(len(y)):
    j0 = np.searchsorted(hs, ds[k[i]], "left")
    first[i] = (hlo[j0] if y.direction[i] == 1 else hhi[j0]) == y.stop_px[i]
mask = ev.trusted.to_numpy().copy()
print("yes rows whose wick extreme is the 18:00 NY reopen bar:", round(first.mean(), 3))
b = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold="10h", keep_trades=True)["_trades"]
b["adj"] = b.net_R - b.ctrl_mean_R
yy = b[b.gate].reset_index(drop=True); comp = b.loc[~b.gate, "adj"].mean()
yy = yy.merge(pd.DataFrame({"decision_time": y.decision_time, "direction": y.direction, "reopen": first}),
              on=["decision_time", "direction"], how="left")
for f in (True, False):
    a = yy.loc[yy.reopen == f, "adj"]
    print(f"  extreme in reopen bar={f}: n={len(a)}, gated adj mean {a.mean():+.4f}, minus complement {a.mean()-comp:+.4f}")
