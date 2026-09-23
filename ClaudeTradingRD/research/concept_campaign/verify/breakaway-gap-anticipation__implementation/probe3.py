"""Is the -1.1pp a nearest-neighbour matching artefact? (1) bias of matched neighbours by distance decile,
(2) caliper matching, (3) placebo: shuffle the overlap label within month x direction and rerun the same matching."""
import numpy as np, pandas as pd
A = pd.read_pickle("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/breakaway-gap-anticipation__implementation/A.pkl")
A["ld"] = np.log(A.dist.clip(lower=1e-6))
A["mon"] = pd.DatetimeIndex(A.t).tz_convert(None).to_period("M").astype(str)
T = pd.DatetimeIndex(A.t).as_unit("ns").asi8; D = A.dir.values; LD = A.ld.values; F = A.fill.values.astype(float)
W = pd.Timedelta(days=30).value

def run(ov, caliper=None, detail=False):
    ei = np.flatnonzero(ov); bi = np.flatnonzero(~ov)
    bt = T[bi]; lo = np.searchsorted(bt, T[ei] - W); hi = np.searchsorted(bt, T[ei] + W)
    o, nl, dd = [], [], []
    for q, e in enumerate(ei):
        cand = np.arange(lo[q], hi[q]); cand = cand[D[bi[cand]] == D[e]]
        if len(cand) < 5: continue
        dif = np.abs(LD[bi[cand]] - LD[e]); sel = cand[np.argsort(dif, kind="stable")[:5]]
        if caliper is not None and (np.abs(LD[bi[sel]] - LD[e]) > caliper).any(): continue
        o.append(F[e]); nl.append(F[bi[sel]].mean()); dd.append((LD[bi[sel]] - LD[e]).mean())
    o, nl, dd = map(np.array, (o, nl, dd))
    return o.mean() - nl.mean(), len(o), o, nl, dd

d, n, o, nl, dd = run(A.ov.values)
print("orig matched diff", round(d, 4), n)
# signed log-dist bias of the neighbours, by event dist decile
ev = A[A.ov].copy()
print("mean(neighbour logdist - event logdist) overall", dd.mean().round(4))
q = pd.qcut(ev.ld.values[:len(dd)] if len(dd) == len(ev) else np.r_[ev.ld.values][:len(dd)], 10, labels=False)
print(pd.DataFrame({"q": q, "dd": dd, "o": o, "nl": nl}).groupby("q").mean().round(4))
for cal in (0.02, 0.05, 0.1):
    d, n, *_ = run(A.ov.values, caliper=cal); print("caliper", cal, "diff", round(d, 4), "n", n)
rng = np.random.default_rng(1)
pl = []
grp = A.groupby(["mon", "dir"]).indices
for r in range(40):
    ov = np.zeros(len(A), bool)
    for k, idx in grp.items():
        m = int(A.ov.values[idx].sum()); ov[rng.choice(idx, m, replace=False)] = True
    pl.append(run(ov)[0])
pl = np.array(pl)
print("placebo (shuffled overlap within month x dir) matched diff: mean %.4f sd %.4f min %.4f max %.4f  share<= -0.0111: %.2f" % (pl.mean(), pl.std(), pl.min(), pl.max(), (pl <= -0.0111).mean()))

# bias-corrected matching (Abadie-Imbens style): adjust neighbour outcome by g(ld_event)-g(ld_nb),
# g = fill rate vs log-dist fitted on the NON-overlap pool (50 quantile bins, linear interp)
base = A[~A.ov]
bins = np.quantile(base.ld, np.linspace(0, 1, 51)); mid = 0.5 * (bins[1:] + bins[:-1])
rate = base.groupby(pd.cut(base.ld, bins, include_lowest=True), observed=False).fill.mean().values
g = lambda x: np.interp(x, mid, rate)
ei = np.flatnonzero(A.ov.values); bi = np.flatnonzero(~A.ov.values)
bt = T[bi]; lo = np.searchsorted(bt, T[ei] - W); hi = np.searchsorted(bt, T[ei] + W)
oo, nn, na, tt = [], [], [], []
for q, e in enumerate(ei):
    cand = np.arange(lo[q], hi[q]); cand = cand[D[bi[cand]] == D[e]]
    if len(cand) < 5: continue
    sel = bi[cand[np.argsort(np.abs(LD[bi[cand]] - LD[e]), kind="stable")[:5]]]
    oo.append(F[e]); nn.append(F[sel].mean()); na.append((F[sel] + g(LD[e]) - g(LD[sel])).mean()); tt.append(T[e])
oo, nn, na = map(np.array, (oo, nn, na))
dif = oo - na
# day-block-ish CI: bootstrap over 5-day buckets
bk = pd.factorize(np.array(tt) // (5 * 86400 * 10**9))[0]
s = pd.DataFrame({"b": bk, "d": dif}).groupby("b").d.agg(["sum", "size"])
rng = np.random.default_rng(0); bs = []
for _ in range(2000):
    i = rng.integers(0, len(s), len(s)); bs.append(s["sum"].values[i].sum() / s["size"].values[i].sum())
print("bias-corrected matched diff %.4f  CI [%.4f, %.4f]  (uncorrected %.4f)" % (dif.mean(), *np.percentile(bs, [2.5, 97.5]), (oo - nn).mean()))
print("excluding top event-dist decile: uncorrected diff %.4f" % ((oo - nn)[LD[ei][:len(oo)] < np.quantile(LD[ei], 0.9)].mean()))
