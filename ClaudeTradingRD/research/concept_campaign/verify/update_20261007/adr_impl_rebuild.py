"""Independent rebuild of average-daily-range u1007a/u1007b (ADR cap rate test) + implementation stress.
Only cl.load_m1() is reused (certified data). Days, ADR, running range, touch (sparse table), nulls: own code.
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

N = int(sys.argv[1]) if len(sys.argv) > 1 else 14
m1 = cl.load_m1()
tn = m1.index.tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy().astype(np.int64)
ny = m1.index.tz_convert("America/New_York").tz_localize(None)
O, H, L = (m1[c].to_numpy(float) for c in ("open", "high", "low"))
nbar = len(tn)

# ---- trading days (roll 18:00 NY): label = date of local+6h
lab = (ny + pd.Timedelta(hours=6)).normalize()
day_id, days = pd.factorize(lab, sort=True)
nd = len(days)
first = np.searchsorted(day_id, np.arange(nd), "left")
last = np.searchsorted(day_id, np.arange(nd), "right") - 1
cnt = last - first + 1
dhi = np.maximum.reduceat(H, first); dlo = np.minimum.reduceat(L, first)
real = cnt >= 600
rr = (dhi - dlo)[real]; ridx = np.flatnonzero(real)
cs = np.concatenate([[0.], np.cumsum(rr)])
k_before = np.searchsorted(ridx, np.arange(nd), "left")      # real days strictly before day d
adr_day = np.where(k_before >= N, (cs[k_before] - cs[np.maximum(k_before - N, 0)]) / N, np.nan)

# ---- per-bar state: running hi/lo of the day from bars BEFORE i (closed by bar i's start)
s = pd.Series(H); g = pd.Series(day_id)
chi = s.groupby(g).cummax().to_numpy(); clo = pd.Series(L).groupby(g).cummin().to_numpy()
rhi = np.r_[np.nan, chi[:-1]]; rlo = np.r_[np.nan, clo[:-1]]
isfirst = np.zeros(nbar, bool); isfirst[first] = True
rhi[isfirst] = np.nan; rlo[isfirst] = np.nan
adr_bar = adr_day[day_id]
left_in_day = last[day_id] + 1 - np.arange(nbar)              # bars from i to day end incl i
csv = np.concatenate([[0.], np.cumsum(H - L)])
ar = np.arange(nbar)
lvol = np.where(ar >= 240, (csv[ar] - csv[np.maximum(ar - 240, 0)]) / 240, np.nan)

# ---- sparse tables for exact range max/min
LV = 11
stH = [H]; stL = [L]
for k in range(1, LV):
    w = 1 << (k - 1)
    a, b = stH[-1], stL[-1]
    stH.append(np.maximum(a, np.r_[a[w:], np.full(w, -np.inf)]))
    stL.append(np.minimum(b, np.r_[b[w:], np.full(w, np.inf)]))
def rmax(lo, hi):   # [lo, hi), hi>lo
    ln = hi - lo; k = np.floor(np.log2(ln)).astype(int); out = np.empty(len(lo))
    for kk in np.unique(k):
        m = k == kk; t = stH[kk]; out[m] = np.maximum(t[lo[m]], t[hi[m] - (1 << kk)])
    return out
def rmin(lo, hi):
    ln = hi - lo; k = np.floor(np.log2(ln)).astype(int); out = np.empty(len(lo))
    for kk in np.unique(k):
        m = k == kk; t = stL[kk]; out[m] = np.minimum(t[lo[m]], t[hi[m] - (1 << kk)])
    return out
def hit(i0, nb, level, side):
    i1 = np.minimum(i0 + nb, nbar); ok = i1 > i0
    out = np.full(len(i0), np.nan)
    u = ok & (side == 1); d = ok & (side == -1)
    out[u] = rmax(i0[u], i1[u]) >= level[u]
    out[d] = rmin(i0[d], i1[d]) <= level[d]
    return out

# ---- events: NY hour closes 19:00..16:00 inside each trading day
start_local = days - pd.Timedelta(hours=6)                     # 18:00 local of open
T = []; D = []
for h in range(1, 23):
    loc = start_local + pd.Timedelta(hours=h)
    T.append(loc.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
             .tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy().astype(np.int64)); D.append(np.arange(nd))
T = np.concatenate(T); D = np.concatenate(D)
i0 = np.searchsorted(tn, T, "left")
inday = (i0 < nbar) & (day_id[np.minimum(i0, nbar - 1)] == D)
ok = inday.copy()
i0 = i0[ok]; T = T[ok]; D = D[ok]
hi_, lo_, a_ = rhi[i0], rlo[i0], adr_bar[i0]
keep = np.isfinite(hi_) & np.isfinite(a_) & ((hi_ - lo_) < a_)
i0, T, D, hi_, lo_, a_ = (x[keep] for x in (i0, T, D, hi_, lo_, a_))
nb = left_in_day[i0]
side = np.r_[np.ones(len(i0)), -np.ones(len(i0))].astype(int)
I0 = np.r_[i0, i0]; TT = np.r_[T, T]; DD = np.r_[D, D]; NB = np.r_[nb, nb]
A = np.r_[a_, a_]; RH = np.r_[hi_, hi_]; RL = np.r_[lo_, lo_]
P0 = O[I0]
print(f"N={N} rows {len(I0)} row-times {len(i0)} days {len(np.unique(D))}")

def evaluate(mult=1.0, rows=None):
    cap = np.where(side == 1, RL + mult * A, RH - mult * A)
    dist = (cap - P0) * side
    obs = hit(I0, NB, cap, side)
    return cap, dist, obs

# ---- null sampler (own RNG): same NY clock minute on another day within +/-30 d, bar must exist
def draw(reps=5, seed=12345, accept=None, maxtry=200):
    rng = np.random.default_rng(seed)
    n = len(I0); out = np.full((n, reps), -1, np.int64)
    locs = pd.DatetimeIndex(TT).tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    for r in range(reps):
        pend = np.arange(n)
        for _ in range(maxtry):
            if not len(pend): break
            kd = rng.integers(-30, 31, len(pend))
            tl = locs[pend] + pd.to_timedelta(kd, unit="D")
            tu = tl.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
            okk = ~pd.isna(tu)
            cand = np.full(len(pend), -1, np.int64)
            tv = tu[okk].tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy().astype(np.int64)
            p = np.searchsorted(tn, tv, "left"); pc = np.minimum(p, nbar - 1)
            good = (tn[pc] == tv) & (kd[okk] != 0)
            cand[np.flatnonzero(okk)[good]] = pc[good]
            acc = cand >= 0
            if accept is not None:
                acc &= accept(pend, np.maximum(cand, 0))
            out[pend[acc], r] = cand[acc]
            pend = pend[~acc]
    return out

def null_rate(J, dist, scale="vol", require=None):
    n, reps = J.shape; res = np.full((n, reps), np.nan)
    ve = lvol[I0]
    for r in range(reps):
        j = J[:, r]; v = j >= 0; jj = np.maximum(j, 0)
        if scale == "vol":
            dd = dist * lvol[jj] / ve
        elif scale == "adr":
            dd = dist * adr_bar[jj] / A
        else:
            dd = dist
        lvl = O[jj] + side * dd
        h = hit(jj, NB, lvl, side)
        good = v & np.isfinite(dd)
        if require is not None:
            good &= require(jj, lvl)
        res[good, r] = h[good]
    return res

def summarise(name, obs, res, mask=None, boot=1000, seed=1):
    nm = np.nanmean(res, axis=1)
    m = np.isfinite(obs) & np.isfinite(nm)
    if mask is not None: m &= mask
    o, c, d = obs[m], nm[m], DD[m]
    diff = o.mean() - c.mean()
    # day-block bootstrap
    u, inv = np.unique(d, return_inverse=True)
    so = np.bincount(inv, o); sc = np.bincount(inv, c); sn = np.bincount(inv)
    rng = np.random.default_rng(seed); bs = []
    for _ in range(boot):
        k = rng.integers(0, len(u), len(u))
        bs.append(so[k].sum() / sn[k].sum() - sc[k].sum() / sn[k].sum())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    yr = pd.DatetimeIndex(days[d]).year
    h1 = yr <= 2020
    print(f"{name:42s} n={m.sum():6d} obs={o.mean():.4f} null={c.mean():.4f} diff={diff:+.4f} "
          f"CI[{lo:+.4f},{hi:+.4f}] H1={o[h1].mean()-c[h1].mean():+.4f} H2={o[~h1].mean()-c[~h1].mean():+.4f}")
    return diff, lo, hi
