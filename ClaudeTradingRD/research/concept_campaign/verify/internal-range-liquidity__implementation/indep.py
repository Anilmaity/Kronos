"""Independent IRL implementation + same-moment nulls (own bootstrap, no ledger writes)."""
import os, sys
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(__file__), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
HERE = os.path.dirname(__file__)
b = cl.bars("1h").reset_index(drop=True)
H, L, C = b.high.to_numpy(), b.low.to_numpy(), b.close.to_numpy(); n = len(b)
# fractal 2/2: strict left, non-strict right; known at close of i+2
sh_ok = np.zeros(n, bool); sl_ok = np.zeros(n, bool)
for i in range(2, n-2):
    sh_ok[i] = H[i] > H[i-1] and H[i] > H[i-2] and H[i] >= H[i+1] and H[i] >= H[i+2]
    sl_ok[i] = L[i] < L[i-1] and L[i] < L[i-2] and L[i] <= L[i+1] and L[i] <= L[i+2]
R = 50
rows = []
act_sh, act_sl = {}, {}          # pos -> level, untaken
bullg, bearg = {}, {}            # pos(3rd bar) -> (near, far)
for j in range(n):
    q = j - 3                    # confirmed at close of j-1
    if q >= 2:
        if sh_ok[q]: act_sh[q] = H[q]
        if sl_ok[q]: act_sl[q] = L[q]
    for dct in (act_sh, act_sl, bullg, bearg):
        for k in [k for k in dct if j - k > R]: del dct[k]
    tk_hi = [k for k, v in act_sh.items() if H[j] > v]
    tk_lo = [k for k, v in act_sl.items() if L[j] < v]
    for k in tk_hi: del act_sh[k]
    for k in tk_lo: del act_sl[k]
    for k in [k for k, g in bullg.items() if L[j] <= g[0]]: del bullg[k]
    for k in [k for k, g in bearg.items() if H[j] >= g[0]]: del bearg[k]
    if j >= 2 and L[j] > H[j-2]: bullg[j] = (L[j], H[j-2])
    if j >= 2 and H[j] < L[j-2]: bearg[j] = (H[j], L[j-2])
    if bool(tk_hi) == bool(tk_lo): continue
    if tk_hi:
        c = [g for g in bullg.values() if g[0] < C[j]]
        if c: g = max(c); rows.append((j, -1, g[0], (g[0]+g[1])/2))
    else:
        c = [g for g in bearg.values() if g[0] > C[j]]
        if c: g = min(c); rows.append((j, 1, g[0], (g[0]+g[1])/2))
r = np.array(rows)
ev = pd.DataFrame({"decision_time": pd.DatetimeIndex(b.close_time.to_numpy()[r[:,0].astype(int)]),
                   "direction": r[:,1].astype(int), "near_edge": r[:,2], "ce": r[:,3], "pos": r[:,0].astype(int)})
orig = pd.read_pickle(os.path.join(HERE, "orig_events.pkl"))
mg = ev.merge(orig, on=["decision_time","direction"], how="outer", indicator=True, suffixes=("","_o"))
print("mine", len(ev), "orig", len(orig), mg._merge.value_counts().to_dict(),
      "ce max absdiff", np.nanmax(np.abs(mg.ce - mg.ce_o)))
mkt = cl.get_market(); t = pd.DatetimeIndex(ev.decision_time); d = ev.direction.to_numpy()
i0 = mkt.pos_at_or_after(t); px0 = mkt.o[np.minimum(i0, len(mkt.o)-1)]
def hit(times, level, dirs):
    out = np.zeros(len(times), bool)
    for s, side in ((1,"above"),(-1,"below")):
        mm = dirs == s
        if mm.any(): out[mm] = cl.touch(times[mm], level[mm], side, horizon_bars=600)["hit"].to_numpy()
    return out
dist = ev.ce.to_numpy() - px0
obs = hit(t, ev.ce.to_numpy(), d)
# ATR14 of 1h bars known at close of bar j
tr = np.maximum(H - L, np.maximum(abs(H - np.r_[np.nan, C[:-1]]), abs(L - np.r_[np.nan, C[:-1]])))
atr = pd.Series(tr).rolling(14).mean().to_numpy()[ev.pos.to_numpy()]
day = cl.trading_day(t) if hasattr(cl, "trading_day") else t.floor("D")
day = pd.Index(day)
def dayboot(x, nb=2000, seed=1):
    g = pd.Series(x).groupby(day.values); s = g.sum().to_numpy(); c = g.count().to_numpy()
    rng = np.random.default_rng(seed); k = len(s)
    idx = rng.integers(0, k, (nb, k)); m = s[idx].sum(1)/c[idx].sum(1)
    return np.percentile(m, [2.5, 97.5])
def report(name, nul):
    diff = obs.mean() - nul.mean(); x = obs - nul; lo, hi = dayboot(x)
    h1 = t < pd.Timestamp("2021-01-01", tz="UTC")
    print(f"{name:32s} obs {obs.mean():.4f} null {nul.mean():.4f} diff {diff:+.4f} dayCI [{lo:+.4f},{hi:+.4f}] H1 {x[h1].mean():+.4f} H2 {x[~h1].mean():+.4f}")
# (A) same moment, same direction, distance in ATR units shuffled among same-direction events within +/-30d
rng = np.random.default_rng(7); tn = t.asi8
nul = np.zeros(len(t)); REPS = 5
z = dist / atr
for rep in range(REPS):
    zz = np.empty(len(t))
    for s in (1, -1):
        ids = np.flatnonzero(d == s)
        for ii, e in enumerate(ids):
            lo_, hi_ = np.searchsorted(tn[ids], [tn[e] - 30*86400e9, tn[e] + 30*86400e9])
            zz[e] = z[ids[rng.integers(lo_, hi_)]]
    nul += hit(t, px0 + zz * atr, d)
report("A same-moment, shuffled ATR-dist", nul / REPS)
# (B) same moment, same raw distance, but opposite side: no — instead raw shuffled distance (not ATR-scaled)
nul = np.zeros(len(t))
for rep in range(REPS):
    zz = np.empty(len(t))
    for s in (1, -1):
        ids = np.flatnonzero(d == s)
        for e in ids:
            lo_, hi_ = np.searchsorted(tn[ids], [tn[e] - 30*86400e9, tn[e] + 30*86400e9])
            zz[e] = dist[ids[rng.integers(lo_, hi_)]]
    nul += hit(t, px0 + zz, d)
report("B same-moment, shuffled raw dist", nul / REPS)
# (C) harness-style random null but ToD-matched (tod 30) -- own bootstrap
rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=30)
nulC = np.zeros(len(t)); cnt = np.zeros(len(t))
for k in range(5):
    tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"); ok = ~tk.isna()
    p = mkt.o[mkt.pos_at_or_after(tk[ok])]
    nulC[ok] += hit(tk[ok], p + dist[ok], d[ok]); cnt[ok] += 1
okc = cnt > 0
x = obs[okc] - nulC[okc]/cnt[okc]
print("C random-moment ToD30 diff", round(x.mean(), 4))
rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)
nulD = np.zeros(len(t))
for k in range(5):
    tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
    p = mkt.o[mkt.pos_at_or_after(tk)]; nulD += hit(tk, p + dist, d)
report("D harness-style random null (mine)", nulD / 5)
