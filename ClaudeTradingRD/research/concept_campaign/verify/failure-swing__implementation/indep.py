"""Independent re-implementation of failure-swing reading b (15m, sweep definition).
Only cl.load_m1() is used from the harness (raw data). Everything else is own code."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

HZN = 300; REPS = 5; W = 30
m1 = cl.load_m1()
t1 = pd.DatetimeIndex(m1.index).tz_convert("UTC")
tn = t1.asi8
O = m1["open"].to_numpy(float); H = m1["high"].to_numpy(float); L = m1["low"].to_numpy(float)
N = len(H)
# forward max/min over [i, i+HZN)
def fwd(x, fn):
    s = pd.Series(x[::-1]).rolling(HZN, min_periods=1)
    return (s.max() if fn == "max" else s.min()).to_numpy()[::-1]
FMAX = fwd(H, "max"); FMIN = fwd(L, "min")

b = m1[["open","high","low","close"]].resample("15min", label="left", closed="left").agg(
    {"open":"first","high":"max","low":"min","close":"last"}).dropna()
bs = pd.DatetimeIndex(b.index).tz_convert("UTC")
bh = b.high.to_numpy(); bl = b.low.to_numpy(); bc = b.close.to_numpy()
pc = np.r_[np.nan, bc[:-1]]
tr = np.nanmax(np.vstack([bh-bl, abs(bh-pc), abs(bl-pc)]), 0)
atr = pd.Series(tr).rolling(14).mean().to_numpy()
n = len(bh)
sh = np.zeros(n, bool); sl = np.zeros(n, bool)
sh[1:-1] = (bh[1:-1] > bh[:-2]) & (bh[1:-1] > bh[2:])
sl[1:-1] = (bl[1:-1] < bl[:-2]) & (bl[1:-1] < bl[2:])

rows = []
for side, x, pts in (("above", bh, np.flatnonzero(sh)), ("below", -bl, np.flatnonzero(sl))):
    for k in range(1, len(pts)):
        p0, p1 = pts[k-1], pts[k]
        conf = p1 + 1
        if conf >= n or not np.isfinite(atr[conf]): continue
        btw = x[p0+1:p1].max() if p1 - p0 > 1 else -np.inf
        fail = (x[p1] < x[p0]) and (btw < x[p0])
        lvl = x[p1] if side == "above" else -x[p1]
        rows.append((bs[conf] + pd.Timedelta("15min"), lvl, side == "above", fail,
                     atr[conf], x[p1] - x[p0]))
ev = pd.DataFrame(rows, columns=["dt", "level", "above", "fail", "atr", "d01"])
ev = ev.sort_values("dt").reset_index(drop=True)
i0 = np.searchsorted(tn, pd.DatetimeIndex(ev.dt).asi8, "left")
ok = i0 < N - HZN
ev = ev[ok].reset_index(drop=True); i0 = i0[ok]
ab = ev.above.to_numpy(); lv = ev.level.to_numpy()
def hit(i, lvl, ab):
    return np.where(ab, FMAX[i] >= lvl, FMIN[i] <= lvl)
ev["hit"] = hit(i0, lv, ab)
dist = lv - O[i0]
ev["dist"] = dist
# atr of the 15m bar series at null time: map M1 index -> last closed 15m bar atr
bclose = (bs + pd.Timedelta("15min")).asi8
def atr_at(i):
    j = np.searchsorted(bclose, tn[i], "right") - 1
    return atr[np.maximum(j, 0)]
ev_atr = atr_at(i0)

rng = np.random.default_rng(7)
q = np.flatnonzero((t1.minute % 15) == 0)          # quarter-hour M1 starts
qn = tn[q]
wns = np.int64(W * 86400e9)
null = np.zeros((len(ev), REPS)); nullv = np.zeros((len(ev), REPS)); nullt = np.full((len(ev), REPS), np.nan)
lo = np.searchsorted(qn, tn[i0] - wns); hi = np.searchsorted(qn, tn[i0] + wns)
ny = t1.tz_convert("America/New_York"); nymin = (ny.hour * 60 + ny.minute).to_numpy()
for r in range(REPS):
    j = q[lo + (rng.random(len(ev)) * (hi - lo)).astype(int)]
    j = np.minimum(j, N - HZN - 1)
    null[:, r] = hit(j, O[j] + dist, ab)
    sc = atr_at(j) / ev_atr
    nullv[:, r] = hit(j, O[j] + dist * sc, ab)
    # time-of-day matched: same NY minute on random other day (+/-30d), exact minute if exists
    kday = rng.integers(1, W + 1, len(ev)) * rng.choice([-1, 1], len(ev))
    tgt = (pd.DatetimeIndex(ev.dt).tz_convert("America/New_York").tz_localize(None)
           + pd.to_timedelta(kday, "D")).tz_localize("America/New_York", ambiguous="NaT",
           nonexistent="NaT").tz_convert("UTC")
    tg = tgt.asi8
    jj = np.searchsorted(tn, tg, "left"); jj = np.minimum(jj, N - HZN - 1)
    good = (~tgt.isna()) & (tn[jj] == tg)
    nullt[good, r] = hit(jj[good], O[jj[good]] + dist[good], ab[good])
ev["null"] = null.mean(1); ev["nullv"] = nullv.mean(1); ev["nullt"] = np.nanmean(nullt, 1)
ev["day"] = pd.DatetimeIndex(ev.dt).tz_convert("America/New_York").normalize()

def boot(d, col):
    g = d.groupby("day").agg(h=("hit", "sum"), nl=(col, "sum"), c=("hit", "size"))
    g = g[np.isfinite(g.nl)]
    hs, ns, cs = g.h.to_numpy(), g.nl.to_numpy(), g.c.to_numpy()
    r = np.random.default_rng(1); idx = r.integers(0, len(g), (2000, len(g)))
    bd = (hs[idx].sum(1) - ns[idx].sum(1)) / cs[idx].sum(1)
    return (hs.sum() - ns.sum()) / cs.sum(), np.percentile(bd, [2.5, 97.5])

for name, d in (("b_fail", ev[ev.fail]), ("nonfail", ev[~ev.fail]), ("all_swings", ev)):
    print(f"\n{name}: n={len(d)}  obs={d.hit.mean():.4f}")
    for col in ("null", "nullv", "nullt"):
        dd = d[d[col].notna()]
        diff, ci = boot(dd, col)
        print(f"  {col:6s} null={dd[col].mean():.4f} diff={diff:+.4f} CI [{ci[0]:+.4f},{ci[1]:+.4f}]  n={len(dd)}")
    for half, m in (("H1", d.dt < pd.Timestamp("2021-01-01", tz="UTC")), ("H2", d.dt >= pd.Timestamp("2021-01-01", tz="UTC"))):
        dd = d[m]; print(f"  {half} diff(null)={dd.hit.mean()-dd.null.mean():+.4f} diff(nullv)={dd.hit.mean()-dd.nullv.mean():+.4f}")
# failure vs non-failure, distance-bucket matched (dist/atr deciles, per side)
ev["dz"] = np.abs(ev.dist) / ev_atr
ev["bk"] = pd.qcut(ev.dz, 20, labels=False, duplicates="drop")
g = ev.groupby(["bk", "above", "fail"]).hit.mean().unstack()
w = ev[ev.fail].groupby(["bk", "above"]).size()
print("\nfail - nonfail within |dist|/ATR ventile x side, weighted by fail count:",
      ((g[True] - g[False]) * w).sum() / w.sum())
ev.to_pickle("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/failure-swing__implementation/ev.pkl")
