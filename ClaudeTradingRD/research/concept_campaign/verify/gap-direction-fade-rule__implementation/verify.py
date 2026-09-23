"""Independent re-implementation of gap-direction-fade-rule reading a + null variants.
Does NOT write results. Scratch verification only."""
import sys, importlib.util
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

H = 60
m1 = cl.load_m1()
mkt = cl.get_market()
tn = mkt.t
ny = tn.tz_convert("America/New_York")
# trading day: NY clock shifted +6h (18:00 NY rolls the day)
tday = (ny.tz_localize(None) + pd.Timedelta("6h")).normalize()
td = pd.Series(tday.values)
new = np.r_[True, td.values[1:] != td.values[:-1]]
starts = np.flatnonzero(new)
ends = np.r_[starts[1:] - 1, len(tn) - 1]
nbars = ends - starts + 1
dh = np.maximum.reduceat(mkt.h, starts); dl = np.minimum.reduceat(mkt.l, starts)
dayidx = pd.DatetimeIndex(td.values[starts])
# week/month keys of the trading day (weeks start with the Sunday-evening session -> Monday trading day)
wk = dayidx.to_period("W-SUN"); mo = dayidx.to_period("M")

rows = []
for j in range(1, len(starts)):
    if nbars[j] <= 600 or nbars[j - 1] <= 600:
        continue
    s = starts[j]
    pc = mkt.c[s - 1]; op = mkt.o[s]
    if op == pc:
        continue
    t = tn[s] + pd.Timedelta("1min")
    if s + 1 >= len(tn) or tn[s + 1] != t:
        # second bar not immediately after; use next available
        pass
    px = mkt.o[s + 1]
    up = op > pc
    if up and not px > pc: continue
    if (not up) and not px < pc: continue
    # prior completed day / week / month extremes
    lv = [(dh[j - 1], dl[j - 1])]
    w_prev = np.flatnonzero(wk[:j] < wk[j])
    if len(w_prev):
        pw = wk[w_prev[-1]]; m = np.flatnonzero(wk[:j] == pw)
        lv.append((dh[m].max(), dl[m].min()))
    m_prev = np.flatnonzero(mo[:j] < mo[j])
    if len(m_prev):
        pm = mo[m_prev[-1]]; m = np.flatnonzero(mo[:j] == pm)
        lv.append((dh[m].max(), dl[m].min()))
    thr = any((pc <= Hh and op > Hh) if up else (pc >= Ll and op < Ll) for Hh, Ll in lv)
    rows.append((t, pc, op, px, up, thr, s + 1, ny[s].dayofweek, dh[j - 1] - dl[j - 1]))
f = pd.DataFrame(rows, columns=["t", "pc", "op", "px", "up", "through", "i0", "dow", "prange"])
print("all unfilled gaps", len(f), "through", f.through.sum())
a = f[~f.through].reset_index(drop=True)
print("reading a n", len(a))

def hit_from(i0, lvl, up):
    out = np.zeros(len(i0), bool)
    for k in range(len(i0)):
        seg = slice(i0[k], min(i0[k] + H, len(tn)))
        out[k] = (mkt.l[seg] <= lvl[k]).any() if up[k] else (mkt.h[seg] >= lvl[k]).any()
    return out

i0 = a.i0.to_numpy(); up = a.up.to_numpy(); lvl = a.pc.to_numpy(); dist = lvl - a.px.to_numpy()
obs = hit_from(i0, lvl, up)
print("obs rate", obs.mean(), "up", obs[up].mean(), "dn", obs[~up].mean())
print("median |dist|/prior range", np.median(np.abs(dist) / a.prange))

t = pd.DatetimeIndex(a.t)

def null_rate(tol, seed=cl.rules.SEED, opposite=False):
    rt = cl.sample_times(t, 5, 30, seed=seed, tod_tol_min=tol)
    res = np.full((len(t), 5), np.nan)
    for k in range(5):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        okk = ~tk.isna()
        p = mkt.pos_at_or_after(tk[okk])
        d = dist[okk] if not opposite else -dist[okk]
        u = up[okk] if not opposite else ~up[okk]
        res[okk, k] = hit_from(p, mkt.o[p] + d, u)
    nymin = []
    for k in range(5):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        loc = tk.tz_convert("America/New_York")
        nymin.append((loc.hour * 60 + loc.minute)[~tk.isna()])
    nm = np.concatenate(nymin)
    return np.nanmean(res, 1), nm

def boot(diff, n=2000):
    rng = np.random.default_rng(0)
    # day-level iid bootstrap (one event per day)
    b = [rng.choice(diff, len(diff)).mean() for _ in range(n)]
    return np.percentile(b, [2.5, 97.5])

for tol in (30, 0):
    nr, nm = null_rate(tol)
    ok = ~np.isnan(nr)
    d = obs[ok] - nr[ok]
    print(f"tol={tol}: n={ok.sum()} null={nr[ok].mean():.4f} diff={d.mean():+.4f} CI={boot(d)} "
          f"| up diff {d[up[ok]].mean():+.4f} dn diff {d[~up[ok]].mean():+.4f} "
          f"| null NY-minute dist: {pd.Series(nm).value_counts().sort_index().head(5).to_dict()} mean {nm.mean():.1f}")
    h1 = t[ok] < pd.Timestamp("2021-01-01", tz="UTC")
    print("   halves", d[h1].mean(), d[~h1].mean())

# Symmetric same-moment null: does price reach an equal-distance level on the OTHER side (away from fill)?
away = np.zeros(len(i0), bool)
for k in range(len(i0)):
    seg = slice(i0[k], min(i0[k] + H, len(tn)))
    L2 = a.px[k] - dist[k]  # mirror
    away[k] = (mkt.h[seg] >= L2).any() if up[k] else (mkt.l[seg] <= L2).any()
d = obs.astype(float) - away
print(f"same-moment mirror: toward={obs.mean():.4f} away={away.mean():.4f} diff={d.mean():+.4f} CI={boot(d)}"
      f" up {d[up].mean():+.4f} dn {d[~up].mean():+.4f}")
h1 = t < pd.Timestamp("2021-01-01", tz="UTC")
print("   halves", d[h1].mean(), d[~h1].mean())
# Sunday reopen vs weekday
sun = (a.dow == 6).to_numpy()
print("sunday n", sun.sum(), "toward", obs[sun].mean(), "away", away[sun].mean(),
      "| weekday toward", obs[~sun].mean(), "away", away[~sun].mean())
a.assign(obs=obs, away=away).to_csv(__file__.replace("verify.py", "events_a.csv"), index=False)
