"""Score the SAME mitigation-block a events as a genuine resting limit at the block open
(fill in the touch minute at the level), vs. the harness's next-open emulation, which
drops every trade whose next M1 open is already beyond the stop."""
import sys, importlib.util
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b")
spec = importlib.util.spec_from_file_location("mb", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b/mitigation-block.py")
mb = importlib.util.module_from_spec(spec); spec.loader.exec_module(mb)
bc, cl = mb.bc, mb.cl
from concept_lab.data import utc_ns
from concept_lab.engine import resolve_trades, sample_times

def detect_a_lvl(m1):
    b = bc.bars(m1)
    legs = bc.displacement_legs(b)
    tdir, _, _ = bc.trend_state(b, legs)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    n = len(b); rows = []
    for j in np.flatnonzero(((tdir == -1) & (c > o)) | ((tdir == 1) & (c < o))):
        d = tdir[j]; end = min(n, j + 1 + mb.BREAK_BARS)
        brk = np.flatnonzero(l[j+1:end] < l[j]) if d == -1 else np.flatnonzero(h[j+1:end] > h[j])
        if len(brk) == 0: continue
        k = j + 1 + int(brk[0]); seg = c[j+1:k+1]
        if (d == -1 and (seg > h[j]).any()) or (d == 1 and (seg < l[j]).any()): continue
        rows.append((j, k, d, o[j], h[j] if d == -1 else l[j]))
    r = pd.DataFrame(rows, columns=["j", "k", "d", "lvl", "stop"])
    start = ct[r["k"].to_numpy()]
    hit, dt = bc.touch_sided(m1, start, r["lvl"].to_numpy(), r["d"].to_numpy(), start + mb.LIVE_BARS * mb.TD)
    r = r[hit].assign(dt=dt[hit])
    ev = pd.DataFrame({"decision_time": pd.DatetimeIndex(r["dt"]), "available_at": pd.DatetimeIndex(r["dt"]),
                       "direction": r["d"].to_numpy(), "stop_px": r["stop"].to_numpy(), "rr": 2.0,
                       "lvl": r["lvl"].to_numpy()})
    return bc.finish(ev.iloc[::-1])

m1 = cl.load_m1(); mkt = cl.get_market(m1)
ev = detect_a_lvl(m1)
ref = pd.read_parquet("ev_a.parquet")
assert len(ev) == len(ref) and np.allclose(ev.stop_px, ref.stop_px) and (ev.decision_time.values == ref.decision_time.values).all()
d = pd.DatetimeIndex(ev.decision_time); dn = utc_ns(d)
sgn = ev.direction.to_numpy(); stop = ev.stop_px.to_numpy(); lvl = ev.lvl.to_numpy()
N = len(mkt.tn)
it = np.searchsorted(mkt.tn, dn - np.int64(60e9), side="left")   # the touch minute
assert (mkt.tn[it] == dn - np.int64(60e9)).all()
i0 = it + 1                                                       # next-open (harness) entry bar
nxt = mkt.o[np.minimum(i0, N-1)]
harness_drop = ~(sgn * (nxt - stop) > 0)
print("events", len(ev), "harness drops (next open beyond stop)", harness_drop.sum())
# genuine limit: fill at lvl (or better, if the touch minute gapped through it)
ot = mkt.o[it]
entry = np.where(sgn < 0, np.maximum(lvl, ot), np.minimum(lvl, ot))
risk = sgn * (entry - stop)
risk_lvl = sgn * (lvl - stop)
ok = risk_lvl > 0
print("lvl==stop (zero-risk) rows removed:", (~ok).sum())
hold = np.timedelta64(150, "m").astype("timedelta64[ns]").astype(np.int64)
i1 = np.searchsorted(mkt.tn, dn + hold, side="left")
tgt = lvl + sgn * 2 * risk_lvl
# touch-minute: stopped if its range also reached the stop (conservative; order unknown)
touch_stop = np.where(sgn < 0, mkt.h[it] >= stop, mkt.l[it] <= stop)
res = resolve_trades(mkt, sgn > 0, stop, tgt, i0, np.maximum(i1, i0 + 1))
gross = sgn * (res["exit_px"] - entry) / risk_lvl
gross = np.where(touch_stop, np.where(sgn*(entry-stop) > 0, -risk/risk_lvl, -1.0), gross)
net = gross - 0.04
# matched control: harness-style, same direction, stop dist = |lvl - stop|, 2R, 150 min, 5 reps ±30d
ct = sample_times(d, 5, 30, cl.rules.SEED, align="auto", m1=m1)
ctf = ct.T.reshape(-1); src = np.tile(np.arange(len(ev)), 5)
has = ~np.isnat(ctf)
ci0 = np.searchsorted(mkt.tn, ctf, side="left"); ci0c = np.minimum(ci0, N-1)
cent = mkt.o[ci0c]; cs = sgn[src]; crisk = risk_lvl[src]
cst = cent - cs * crisk; ctg = cent + cs * 2 * crisk
ci1 = np.searchsorted(mkt.tn, np.where(has, ctf, mkt.tn[0]) + np.timedelta64(150, "m"), side="left")
cok = has & (ci0 < N) & (ci1 > ci0) & ok[src]
cr = resolve_trades(mkt, cs[cok] > 0, cst[cok], ctg[cok], ci0[cok], ci1[cok])
cnet = cs[cok] * (cr["exit_px"] - cent[cok]) / crisk[cok] - 0.04
cm = pd.Series(cnet).groupby(src[cok]).mean().reindex(range(len(ev))).to_numpy()
def book(mask, label):
    g = mask & ok & np.isfinite(cm)
    x = net[g] - cm[g]
    days = pd.DatetimeIndex(d[g]).tz_convert("America/New_York").normalize()
    s = pd.Series(x).groupby(days.values).agg(["sum", "count"])
    rng = np.random.default_rng(1); S, C = s["sum"].to_numpy(), s["count"].to_numpy(); m = len(S)
    bs = []
    for _ in range(2000):
        ix = rng.integers(0, m, m); bs.append(S[ix].sum()/C[ix].sum())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    h1 = d[g] < pd.Timestamp("2021-01-01", tz="UTC")
    print(f"{label:48s} n={g.sum():6d} real={net[g].mean():+.4f} ctrl={cm[g].mean():+.4f} diff={x.mean():+.4f} "
          f"CI[{lo:+.4f},{hi:+.4f}] H1={x[h1].mean():+.4f} H2={x[~h1].mean():+.4f}")
book(~harness_drop, "limit fill, harness-surviving events only")
book(np.ones(len(ev), bool), "limit fill, ALL events (incl. harness drops)")
print("harness-dropped events under limit fill: mean net", net[harness_drop & ok].mean(), "n", (harness_drop&ok).sum())
print("touch-minute stops overall:", touch_stop.mean())
