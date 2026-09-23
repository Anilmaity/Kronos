"""Independent re-implementation (no concept_lab): own 5m bars, own detector, own M1 resolver,
own matched random control (same dir, same stop dist, 2R, 50 min, +-30d, NY tod +-30min)."""
import numpy as np, pandas as pd, sys
VARIANT = sys.argv[1] if len(sys.argv) > 1 else "orig"
m1 = pd.read_parquet('/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xau_m1_full.parquet')
m1 = m1[(m1.time >= "2016-01-01 13:19") & (m1.time <= "2026-07-23 04:07")].drop_duplicates("time").reset_index(drop=True)
T = m1.time.values.astype("datetime64[m]").astype(np.int64)  # minutes
O,H,L,C = (m1[k].to_numpy(float) for k in ("open","high","low","close"))
# 5m bars
g = T // 5
bid, start = np.unique(g, return_index=True)
end = np.r_[start[1:], len(T)]
bo = O[start]; bc = C[end-1]
bh = np.maximum.reduceat(H, start); bl = np.minimum.reduceat(L, start)
bclose = bid*5 + 5                           # nominal close minute
lo_prev = pd.Series(bl).rolling(20).min().shift(1).to_numpy()
hi_prev = pd.Series(bh).rolling(20).max().shift(1).to_numpy()
body = np.abs(bc-bo)
if VARIANT == "wick":   # classical: lower wick (min(o,c)-l) > body
    lw = np.minimum(bo,bc)-bl; uw = bh-np.maximum(bo,bc)
else:
    lw = bo-bl; uw = bh-bo
ham = (bl<lo_prev)&(bc>lo_prev)&(lw>body)
sho = (bh>hi_prev)&(bc<hi_prev)&(uw>body)
if VARIANT == "nostopbar":  # sanity: same events
    pass
both = ham&sho; ham&=~both; sho&=~both
idx = np.r_[np.flatnonzero(ham), np.flatnonzero(sho)]
dirn = np.r_[np.ones(ham.sum()), -np.ones(sho.sum())]
dec = bclose[idx]; stop = np.where(dirn>0, bl[idx], bh[idx])
print("events", len(idx))

HOLD = 50
def resolve(dec_min, d, stopdist):
    """entry = open of first M1 with start >= dec; stop/target from entry; stop-first; exit at
    last M1 close with start < dec+HOLD. returns R (gross) and valid mask"""
    e = np.searchsorted(T, dec_min)
    ok = e < len(T)
    e = np.minimum(e, len(T)-1)
    ent = O[e]
    sd = stopdist
    lim = np.searchsorted(T, dec_min + HOLD)          # bars with T < dec+HOLD
    ok &= lim > e
    R = np.full(len(e), np.nan); done = np.zeros(len(e), bool)
    for k in range(HOLD+10):
        j = e + k
        act = ok & ~done & (j < lim)
        if not act.any(): break
        jj = np.minimum(j, len(T)-1)
        hi, lo, op = H[jj], L[jj], O[jj]
        # long view: adverse = entry - low ; favourable = high - entry
        adv = np.where(d>0, ent-lo, hi-ent); fav = np.where(d>0, hi-ent, ent-lo)
        opadv = np.where(d>0, ent-op, op-ent)
        gap = act & (k>0) & (opadv >= sd)
        R[gap] = -opadv[gap]/sd[gap]; done |= gap
        act &= ~gap
        s = act & (adv >= sd); R[s] = -1; done |= s
        t = act & ~s & (fav >= 2*sd); R[t] = 2; done |= t
    last = np.maximum(lim-1, e)
    te = ok & ~done
    R[te] = (np.where(d>0, C[last]-ent, ent-C[last]))[te]/sd[te]
    return R, ok, ent

e0 = np.searchsorted(T, dec); ent0 = O[np.minimum(e0,len(T)-1)]
sd = dirn*(ent0-stop)
valid = sd > 0
dec, dirn, sd = dec[valid], dirn[valid], sd[valid]
R, ok, _ = resolve(dec, dirn, sd)
dec, dirn, sd, R = dec[ok], dirn[ok], sd[ok], R[ok]
print("trades", len(R), "gross avgR", R.mean())

# control: 5 random M1 minutes within +-30 days with NY minute-of-day within +-30
rng = np.random.default_rng(12345)
ny = pd.to_datetime(T, unit="m", utc=True).tz_convert("America/New_York")
nymod = (ny.hour*60+ny.minute).to_numpy()
evny = pd.to_datetime(dec, unit="m", utc=True).tz_convert("America/New_York"); evmod = (evny.hour*60+evny.minute).to_numpy()
REPS=5
ctrlR = np.full((len(dec),REPS), np.nan)
lo_i = np.searchsorted(T, dec-30*1440); hi_i = np.searchsorted(T, dec+30*1440)
for r in range(REPS):
    pick = np.full(len(dec), -1)
    need = np.ones(len(dec), bool)
    for att in range(60):
        cand = rng.integers(lo_i, hi_i)
        dm = np.abs(nymod[cand]-evmod); dm = np.minimum(dm, 1440-dm)
        good = need & (dm <= 30)
        pick[good] = cand[good]; need &= ~good
        if not need.any(): break
    ctrl_dec = np.where(pick>=0, T[np.maximum(pick,0)], dec)
    rr, okc, _ = resolve(ctrl_dec, dirn, sd)
    rr[~okc | (pick<0)] = np.nan
    ctrlR[:,r] = rr
cm = np.nanmean(ctrlR, axis=1)
diff = R - cm
m = ~np.isnan(diff)
yrs = pd.to_datetime(dec, unit="m")
print("control avgR", np.nanmean(ctrlR), "diff", diff[m].mean())
# day-block bootstrap
day = (dec//1440)
df = pd.DataFrame({"day":day[m], "d":diff[m]}).groupby("day").d.agg(["sum","count"])
s, c = df["sum"].to_numpy(), df["count"].to_numpy()
bs = []
b = np.random.default_rng(1)
for _ in range(2000):
    k = b.integers(0, len(s), len(s)); bs.append(s[k].sum()/c[k].sum())
print("day-boot CI", np.percentile(bs,[2.5,97.5]))
h1 = m & (yrs < "2021-01-01"); h2 = m & (yrs >= "2021-01-01")
print("H1", diff[h1].mean(), "H2", diff[h2].mean())
for y in range(2016,2027):
    k = m & (yrs.year==y); print(y, k.sum(), round(diff[k].mean(),4), round(R[k].mean(),4))
# by direction and by stop size quintile (in R-equivalent $)
print("long", diff[m&(dirn>0)].mean(), "short", diff[m&(dirn<0)].mean())
q = pd.qcut(sd[m], 5, labels=False)
print(pd.Series(diff[m]).groupby(q).agg(["mean","count"]))
pd.DataFrame({"dec":dec,"dir":dirn,"sd":sd,"R":R,"cm":cm}).to_pickle(f"indep_{VARIANT}.pkl")
