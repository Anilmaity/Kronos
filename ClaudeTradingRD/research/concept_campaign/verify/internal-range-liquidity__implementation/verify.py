"""Verification of internal-range-liquidity reading a (implementation / look-ahead lens).
Run with CONCEPT_LAB_LEDGER pointed at a scratch file so the campaign ledger is untouched."""
import os, sys, importlib.util
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

ORIG = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02a/internal-range-liquidity.py"
spec = importlib.util.spec_from_file_location("irl_orig", ORIG)
orig = importlib.util.module_from_spec(spec); sys.path.insert(0, os.path.dirname(ORIG)); spec.loader.exec_module(orig)

H = 600
m1 = cl.load_m1()
mkt = cl.get_market()


# ---------------- independent implementation ----------------
def my_detect(m1, range_bars=50, k=2, return_all_sweeps=False):
    b = cl.build_bars(m1, "1h")
    H_, L_, C_ = b.high.to_numpy(), b.low.to_numpy(), b.close.to_numpy()
    n = len(b)
    # fractal swings: strictly above left k, >= right k
    swh = np.zeros(n, bool); swl = np.zeros(n, bool)
    for i in range(k, n - k):
        swh[i] = H_[i] > H_[i-k:i].max() and H_[i] >= H_[i+1:i+k+1].max()
        swl[i] = L_[i] < L_[i-k:i].min() and L_[i] <= L_[i+1:i+k+1].min()
    highs, lows = {}, {}   # pos -> level, live (untaken, confirmed)
    bullg, bearg = {}, {}  # created pos -> (near, far)
    ev, sweeps = [], []
    for j in range(n):
        # swing at i is known after bar i+k closes, usable from bar i+k+1
        i = j - k - 1
        if i >= k:
            if swh[i]: highs[i] = H_[i]
            if swl[i]: lows[i] = L_[i]
        for d in (highs, lows):
            for q in [q for q in d if j - q > range_bars]: del d[q]
        bs = [q for q, v in highs.items() if H_[j] > v]
        ss = [q for q, v in lows.items() if L_[j] < v]
        for q in bs: del highs[q]
        for q in ss: del lows[q]
        # FVG state after bar j: remove touched / stale, then add new
        for q in [q for q, g in bullg.items() if j - q > range_bars or L_[j] <= g[0]]: del bullg[q]
        for q in [q for q, g in bearg.items() if j - q > range_bars or H_[j] >= g[0]]: del bearg[q]
        if j >= 2 and L_[j] > H_[j-2]: bullg[j] = (L_[j], H_[j-2])
        if j >= 2 and H_[j] < L_[j-2]: bearg[j] = (H_[j], L_[j-2])
        if bool(bs) == bool(ss):
            continue
        dirn = -1 if bs else 1
        sweeps.append((j, dirn))
        if dirn == -1:
            c = [g for g in bullg.values() if g[0] < C_[j]]
            if c:
                g = max(c); ev.append((j, -1, g[0], (g[0]+g[1])/2))
        else:
            c = [g for g in bearg.values() if g[0] > C_[j]]
            if c:
                g = min(c); ev.append((j, 1, g[0], (g[0]+g[1])/2))
    ct = b.close_time.to_numpy()
    e = pd.DataFrame(ev, columns=["pos", "direction", "near_edge", "ce"])
    e.insert(0, "decision_time", pd.DatetimeIndex(ct[e.pos.to_numpy()]))
    s = pd.DataFrame(sweeps, columns=["pos", "direction"])
    s.insert(0, "t", pd.DatetimeIndex(ct[s.pos.to_numpy()]))
    return e, s


def hit(times, level, dirs, hb=H):
    out = np.zeros(len(times), bool)
    for sgn, side in ((1, "above"), (-1, "below")):
        m = dirs == sgn
        if m.any():
            out[m] = cl.touch(times[m], level[m], side, horizon_bars=hb)["hit"].to_numpy()
    return out


def px_at(t):
    return mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]


def day_block_ci(x, t, nb=2000, seed=1):
    # simple trading-day cluster bootstrap on per-event paired differences
    day = pd.DatetimeIndex(t).tz_convert("America/New_York").normalize()
    codes, uniq = pd.factorize(day)
    s = np.bincount(codes, weights=x); c = np.bincount(codes)
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(nb):
        idx = rng.integers(0, len(s), len(s))
        bs.append(s[idx].sum() / c[idx].sum())
    return x.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def halves(x, t):
    tt = pd.DatetimeIndex(t)
    m = tt < pd.Timestamp("2021-01-01", tz="UTC")
    return x[m].mean(), x[~m].mean()


if __name__ == "__main__":
    # 1. re-run original detector + test exactly
    ev = orig.detect(m1)
    t = pd.DatetimeIndex(ev.decision_time); d = ev.direction.to_numpy(int)
    print("orig n", len(ev), "fp", cl.frame_fingerprint(ev))
    px0 = px_at(t); rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)
    lvl = ev.near_edge.to_numpy(float); dist = lvl - px0
    obs = hit(t, lvl, d)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"); ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        out[ok] = hit(tk[ok], px_at(tk[ok]) + dist[ok], d[ok]); return out
    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="+", predictors=ev)
    print("RERUN", res["n"], round(res["observed_rate"], 4), round(res["null_rate"], 4),
          round(res["diff"], 4), round(res["ci_lo"], 4), round(res["ci_hi"], 4), res["verdict"])

    # 2. independent implementation
    me, sw = my_detect(m1)
    print("mine n", len(me), "sweeps", len(sw))
    a = ev.set_index("decision_time")[["direction", "near_edge"]]
    bq = me.set_index("decision_time")[["direction", "near_edge"]]
    j = a.join(bq, how="outer", lsuffix="_o", rsuffix="_m")
    same = (j.direction_o == j.direction_m) & np.isclose(j.near_edge_o, j.near_edge_m)
    print("rows identical", int(same.sum()), "of union", len(j))
    t2 = pd.DatetimeIndex(me.decision_time); d2 = me.direction.to_numpy(int)
    l2 = me.near_edge.to_numpy(float); dist2 = l2 - px_at(t2)
    obs2 = hit(t2, l2, d2)
    rt2 = cl.sample_times(t2, 5, 30, seed=cl.rules.SEED)
    nulls = []
    for k in range(5):
        tk = pd.DatetimeIndex(rt2[:, k]).tz_localize("UTC"); ok = ~tk.isna()
        o = np.full(len(t2), np.nan); o[ok] = hit(tk[ok], px_at(tk[ok]) + dist2[ok], d2[ok]); nulls.append(o)
    nm = np.nanmean(np.vstack(nulls), 0)
    x = obs2 - nm
    print("MINE random-time null: obs %.4f null %.4f diff %.4f CI[%.4f,%.4f]" % ((obs2.mean(), np.nanmean(nm)) + day_block_ci(x, t2)), "halves", halves(x, t2))

    # 3. ToD-matched null (trap 9)
    rt3 = cl.sample_times(t2, 5, 30, seed=cl.rules.SEED, tod_tol_min=30)
    nulls = []
    for k in range(5):
        tk = pd.DatetimeIndex(rt3[:, k]).tz_localize("UTC"); ok = ~tk.isna()
        o = np.full(len(t2), np.nan); o[ok] = hit(tk[ok], px_at(tk[ok]) + dist2[ok], d2[ok]); nulls.append(o)
    nm3 = np.nanmean(np.vstack(nulls), 0); ok3 = ~np.isnan(nm3); x3 = obs2[ok3] - nm3[ok3]
    print("ToD null: obs %.4f null %.4f diff %.4f CI[%.4f,%.4f]" % ((obs2[ok3].mean(), nm3[ok3].mean()) + day_block_ci(x3, t2[ok3])), "halves", halves(x3, t2[ok3]))

    # 4. post-sweep null: same distance/side applied at OTHER same-direction sweep bars within +/-30d
    rng = np.random.default_rng(cl.rules.SEED)
    swt = pd.DatetimeIndex(sw.t); swn = swt.asi8; swd = sw.direction.to_numpy()
    tn = t2.asi8; W = 30 * 86400 * 10**9
    nulls = []
    for k in range(5):
        pick = np.empty(len(t2), "int64")
        for i in range(len(t2)):
            cand = np.flatnonzero((swd == d2[i]) & (np.abs(swn - tn[i]) <= W) & (swn != tn[i]))
            pick[i] = swn[rng.choice(cand)]
        tk = pd.DatetimeIndex(pick).tz_localize("UTC")
        nulls.append(hit(tk, px_at(tk) + dist2, d2))
    nm4 = np.mean(np.vstack(nulls), 0); x4 = obs2 - nm4
    print("POST-SWEEP null: obs %.4f null %.4f diff %.4f CI[%.4f,%.4f]" % ((obs2.mean(), nm4.mean()) + day_block_ci(x4, t2)), "halves", halves(x4, t2))

    # 4b. post-sweep null restricted to sweeps where NO FVG candidate existed
    has = set(me.pos.tolist()); nofvg = ~sw.pos.isin(has).to_numpy()
    nulls = []
    for k in range(5):
        pick = np.full(len(t2), -1, "int64")
        for i in range(len(t2)):
            cand = np.flatnonzero(nofvg & (swd == d2[i]) & (np.abs(swn - tn[i]) <= W))
            if len(cand): pick[i] = swn[rng.choice(cand)]
        ok = pick >= 0; o = np.full(len(t2), np.nan)
        tk = pd.DatetimeIndex(pick[ok]).tz_localize("UTC"); o[ok] = hit(tk, px_at(tk) + dist2[ok], d2[ok]); nulls.append(o)
    nm5 = np.nanmean(np.vstack(nulls), 0); ok5 = ~np.isnan(nm5); x5 = obs2[ok5] - nm5[ok5]
    print("POST-SWEEP no-FVG null: n %d obs %.4f null %.4f diff %.4f CI[%.4f,%.4f]" % ((ok5.sum(), obs2[ok5].mean(), nm5[ok5].mean()) + day_block_ci(x5, t2[ok5])), "halves", halves(x5, t2[ok5]))

    # 5. direction-flip: same |dist| on the continuation side at the same moment
    px2 = px_at(t2)
    flip = hit(t2, px2 - dist2, -d2)
    print("same moment: FVG-side hit %.4f vs continuation-side same distance %.4f" % (obs2.mean(), flip.mean()))
