"""Independent reading-a implementation from the YAML: own 2/2 fractals, trend = direction of the
latest close-through of a confirmed swing (BOS state, no displacement gate), opposing-close candle,
near extreme broken within 16 bars (no close beyond far extreme), limit at candle OPEN live 16 bars,
stop at far extreme, 2R, 150 min. Scored (1) as a genuine limit fill and (2) harness-style next-open
with drops, both vs a matched random control (same dir/stop dist, ±30 d, 5 reps, quarter-hour grid)."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
from concept_lab.data import utc_ns
from concept_lab.engine import resolve_trades, sample_times
m1 = cl.load_m1(); mkt = cl.get_market(m1); N = len(mkt.tn)
b = cl.build_bars(m1, "15min")
o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
ct = utc_ns(pd.DatetimeIndex(b["close_time"]))
n = len(b)
sh = np.zeros(n, bool); sl = np.zeros(n, bool)
for i in range(2, n-2):
    sh[i] = h[i] > max(h[i-2], h[i-1], h[i+1], h[i+2])
    sl[i] = l[i] < min(l[i-2], l[i-1], l[i+1], l[i+2])
trend = np.zeros(n, int); cur = 0; lsh = lsl = None
for i in range(n):
    p = i - 3
    if p >= 0 and sh[p]: lsh = h[p]
    if p >= 0 and sl[p]: lsl = l[p]
    if lsh is not None and c[i] > lsh: cur = 1; lsh = None
    if lsl is not None and c[i] < lsl: cur = -1; lsl = None
    trend[i] = cur
TRN = sys.argv[1] if len(sys.argv) > 1 else "bos"
rows = []
for j in np.flatnonzero(((trend == -1) & (c > o)) | ((trend == 1) & (c < o))):
    d = trend[j]
    for k in range(j+1, min(n, j+17)):
        if (d == -1 and c[k] > h[j]) or (d == 1 and c[k] < l[j]): break   # far extreme closed through
        if (d == -1 and l[k] < l[j]) or (d == 1 and h[k] > h[j]):
            rows.append((j, k, d, o[j], h[j] if d == -1 else l[j])); break
r = pd.DataFrame(rows, columns=["j", "k", "d", "lvl", "stop"])
r = r[(r.d * (r.lvl - r.stop)) > 0].reset_index(drop=True)
# first M1 touch after block forms, within 16 bars; own scan
st = ct[r.k.to_numpy()]; en = st + np.int64(16*15*60e9)
a = np.searchsorted(mkt.tn, st, "left"); z = np.searchsorted(mkt.tn, en, "left")
touch = np.full(len(r), -1)
for q, (aa, zz, d, lv) in enumerate(zip(a, z, r.d.to_numpy(), r.lvl.to_numpy())):
    seg = mkt.h[aa:zz] >= lv if d == -1 else mkt.l[aa:zz] <= lv
    f = np.flatnonzero(seg)
    if len(f): touch[q] = aa + f[0]
r = r[touch >= 0].assign(it=touch[touch >= 0])
r = r.sort_values(["it", "j"]).drop_duplicates(["it", "d"], keep="last").reset_index(drop=True)
it = r.it.to_numpy(); sgn = r.d.to_numpy(); lvl = r.lvl.to_numpy(); stop = r.stop.to_numpy()
dn = mkt.tn[it] + np.int64(60e9); d_idx = pd.to_datetime(dn, utc=True)
i0 = it + 1
hold = np.int64(150*60e9); i1 = np.maximum(np.searchsorted(mkt.tn, dn + hold, "left"), i0 + 1)
ok = i0 < N
ct_ = sample_times(d_idx, 5, 30, cl.rules.SEED, align="auto", m1=m1)
ctf = ct_.T.reshape(-1); src = np.tile(np.arange(len(r)), 5); has = ~np.isnat(ctf)
ci0 = np.searchsorted(mkt.tn, ctf, "left"); ci0c = np.minimum(ci0, N-1)
ci1 = np.searchsorted(mkt.tn, np.where(has, ctf, mkt.tn[0]) + np.timedelta64(150, "m"), "left")
def ctrl(riskv):
    cent = mkt.o[ci0c]; cs = sgn[src]; cr_ = riskv[src]
    cok = has & (ci0 < N) & (ci1 > ci0) & np.isfinite(cr_) & (cr_ > 0)
    rr = resolve_trades(mkt, cs[cok] > 0, (cent - cs*cr_)[cok], (cent + cs*2*cr_)[cok], ci0[cok], ci1[cok])
    x = cs[cok]*(rr["exit_px"] - cent[cok])/cr_[cok] - 0.04
    return pd.Series(x).groupby(src[cok]).mean().reindex(range(len(r))).to_numpy()
def report(net, cm, g, label):
    g = g & np.isfinite(cm) & np.isfinite(net); x = net[g] - cm[g]
    days = pd.DatetimeIndex(d_idx[g]).tz_convert("America/New_York").normalize()
    s = pd.Series(x).groupby(days.values).agg(["sum", "count"]); S, C = s["sum"].to_numpy(), s["count"].to_numpy()
    rng = np.random.default_rng(1); bs = [S[ix].sum()/C[ix].sum() for ix in (rng.integers(0, len(S), len(S)) for _ in range(2000))]
    lo, hi = np.percentile(bs, [2.5, 97.5]); h1 = d_idx[g] < pd.Timestamp("2021-01-01", tz="UTC")
    print(f"{label:40s} n={g.sum():6d} real={net[g].mean():+.4f} ctrl={cm[g].mean():+.4f} diff={x.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] H1={x[h1].mean():+.4f} H2={x[~h1].mean():+.4f}")
# (2) harness-style next open
ent = mkt.o[np.minimum(i0, N-1)]; risk = sgn*(ent - stop); good = ok & (risk > 0)
rs = np.where(good, risk, np.nan)
res = resolve_trades(mkt, sgn > 0, stop, ent + sgn*2*np.where(good, risk, 1), i0, i1)
net2 = sgn*(res["exit_px"] - ent)/rs - 0.04
report(net2, ctrl(rs), good, "next-open, drops (harness-style)")
print("  dropped", (~good).sum(), "of", len(r))
# (1) genuine limit
ot = mkt.o[it]; entL = np.where(sgn < 0, np.maximum(lvl, ot), np.minimum(lvl, ot)); rl = sgn*(lvl - stop)
tstop = np.where(sgn < 0, mkt.h[it] >= stop, mkt.l[it] <= stop)
res = resolve_trades(mkt, sgn > 0, stop, lvl + sgn*2*rl, i0, i1)
g1 = sgn*(res["exit_px"] - entL)/rl
g1 = np.where(tstop, np.minimum(sgn*(stop - entL)/rl, 0), g1)
cmL = ctrl(rl)
report(g1 - 0.04, cmL, ok, "genuine limit fill, all")
report(g1 - 0.04, cmL, ok & good, "genuine limit fill, harness survivors")
