"""Step 2: build the controls and run race + trade variants on events and controls.

Controls (all +/-30 d, NY time-of-day within 30 min, 5 accepted draws per event):
  base      campaign null (no ToD match), same up/dn distances, same direction
  tod       same, ToD-matched
  sstop     STRUCTURAL STOP: invalidation/stop placed at the extreme of the prior 1-3
            15m candles (incl. the partial candle up to t), the k whose distance is
            closest to the event's dn, accepted within +/-20%; target = event's up
  sstop_rd  same, direction drawn at random (coin flip) instead of the event's
  sboth     STRUCTURAL BOTH SIDES: stop as sstop AND target = the extreme of the last
            k'=1..96 15m candles on the other side (a real recent swing extreme, like the
            leg extreme), closest to the event's up, accepted within +/-20%
"""
import numpy as np
import pandas as pd
from sim import cl, simulate, pos, market, prior_extreme

OUT = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/deepdive/fvg-three-levels/"
S = pd.read_pickle(OUT + "s1.pkl")
ev, up, dn = S["ev"], S["up"], S["dn"]
t = pd.DatetimeIndex(ev["decision_time"]); d = ev["direction"].to_numpy()
n = len(t)
M = market(); mk = M["mk"]
TOL = 0.20
NC = 60
REPS = 5


def partial_ext(i0):
    """low/high of the M1 bars of the current (incomplete) 15m bucket before i0."""
    lo = np.full(len(i0), np.inf); hi = np.full(len(i0), -np.inf)
    b0 = M["bidx"][np.minimum(i0, len(mk.o) - 1)]
    for j in range(1, 15):
        ij = i0 - j
        okj = (ij >= 0) & (M["bidx"][np.maximum(ij, 0)] == b0)
        lo = np.where(okj, np.minimum(lo, mk.l[np.maximum(ij, 0)]), lo)
        hi = np.where(okj, np.maximum(hi, mk.h[np.maximum(ij, 0)]), hi)
    return lo, hi


def struct_levels(i0, dd, kmax):
    """distance from entry open to the (own-side) extreme of last k complete buckets +
    partial bucket, k=1..kmax; returns array (len, kmax) of distances for own side
    (stop side: below for long) and other side (target side: above for long)."""
    E = mk.o[i0]
    plo, phi = partial_ext(i0)
    own = np.full((len(i0), kmax), np.nan); oth = np.full((len(i0), kmax), np.nan)
    nb_done = np.searchsorted(M["blast"], i0, side="left")
    lo = plo.copy(); hi = phi.copy()
    for k in range(1, kmax + 1):
        b = nb_done - k
        okb = b >= 0
        bb = np.where(okb, b, 0)
        lo = np.where(okb, np.minimum(lo, M["blo"][bb]), np.nan)
        hi = np.where(okb, np.maximum(hi, M["bhi"][bb]), np.nan)
        own[:, k - 1] = np.where(dd > 0, E - lo, hi - E)
        oth[:, k - 1] = np.where(dd > 0, hi - E, E - lo)
    return own, oth


rng = np.random.default_rng(20260923)
cand = cl.sample_times(t, NC, 30, seed=cl.rules.SEED + 11, tod_tol_min=30)
print("candidates drawn", np.isfinite(cand.astype("int64").astype(float)).mean() if False else cand.shape)
rt_tod = cl.sample_times(t, REPS, 30, seed=cl.rules.SEED, tod_tol_min=30)

res = {"obs": S["obs"], "base": S["null_base"]}
res["tod_i0"] = np.vstack([pos(pd.DatetimeIndex(rt_tod[:, k]).tz_localize("UTC")) for k in range(REPS)]).T
res["tod"] = [simulate(pos(pd.DatetimeIndex(rt_tod[:, k]).tz_localize("UTC")), d, up, dn) for k in range(REPS)]
print("tod done")

# ---------- structural controls -----------------------------------------------------
flat_t = pd.DatetimeIndex(cand.reshape(-1)).tz_localize("UTC")
valid = ~flat_t.isna()
i0c = np.zeros(len(flat_t), dtype=np.int64)
i0c[valid] = pos(flat_t[valid])
i0c = np.minimum(i0c, len(mk.o) - 1)
ev_idx = np.repeat(np.arange(n), NC)
d_ev = d[ev_idx]
d_rd = rng.choice([-1, 1], size=len(flat_t))
dn_ev = dn[ev_idx]; up_ev = up[ev_idx]


def pick(ok_mat, score_mat, dist_mat):
    """per candidate: choose column with best score among ok; return dist, ok flag"""
    sc = np.where(ok_mat, score_mat, np.inf)
    j = np.argmin(sc, 1)
    r = np.arange(len(j))
    return dist_mat[r, j], np.isfinite(sc[r, j])


def choose(acc):
    """first REPS accepted candidates per event -> indices into flat arrays (-1 if none)"""
    A = acc.reshape(n, NC)
    sel = np.full((n, REPS), -1, dtype=np.int64)
    cs = np.cumsum(A, 1)
    for k in range(REPS):
        m = A & (cs == k + 1)
        has = m.any(1)
        sel[has, k] = np.flatnonzero(m.reshape(-1)) if False else (np.arange(n)[has] * NC + np.argmax(m[has], 1))
    return sel


for name, dd, need_tgt in (("sstop", d_ev, False), ("sstop_rd", d_rd, False), ("sboth", d_ev, True)):
    own, oth = struct_levels(i0c, dd, 96 if need_tgt else 3)
    own3 = own[:, :3]
    rel = np.abs(own3 / dn_ev[:, None] - 1)
    sd, oks = pick((own3 > 0) & (rel <= TOL), rel, own3)
    acc = oks & valid
    if need_tgt:
        relt = np.abs(oth / up_ev[:, None] - 1)
        tdist, okt = pick((oth > 0) & (relt <= TOL), relt, oth)
        acc &= okt
    else:
        tdist = up_ev
    sel = choose(acc)
    print(name, "accept rate/cand", round(acc.mean(), 3), "events with 5 reps", (sel >= 0).all(1).mean().round(3),
          ">=1", (sel >= 0).any(1).mean().round(3))
    arms = []
    for k in range(REPS):
        s = sel[:, k]
        has = s >= 0
        ii = np.where(has, i0c[np.maximum(s, 0)], len(mk.o) + 10)   # out-of-range -> nan
        ii = np.where(has, ii, 0)
        u_ = np.where(has, tdist[np.maximum(s, 0)], np.nan)
        n_ = np.where(has, sd[np.maximum(s, 0)], np.nan)
        arms.append(simulate(ii, dd[np.maximum(s, 0)], u_, n_))
        # the "same times, same structural distances but NO structure" is what base/tod are
    res[name] = arms
    res[name + "_sel"] = dict(i0=np.where(sel >= 0, i0c[np.maximum(sel, 0)], -1), d=dd[np.maximum(sel, 0)],
                              sd=np.where(sel >= 0, sd[np.maximum(sel, 0)], np.nan))
    res[name + "_dist"] = (np.where(sel >= 0, sd[np.maximum(sel, 0)], np.nan),
                           np.where(sel >= 0, tdist[np.maximum(sel, 0)], np.nan))
pd.to_pickle(res, OUT + "s2.pkl")
print("saved")
