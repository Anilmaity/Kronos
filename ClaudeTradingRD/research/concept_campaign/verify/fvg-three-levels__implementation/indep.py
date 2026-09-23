"""Independent re-implementation: own 15m bars, own FVG, own first return, own 3-way race."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
m1 = cl.load_m1()
T = m1.index.tz_convert("UTC").values.astype("datetime64[ns]").astype(np.int64)
O,H,L,C = (m1[c].to_numpy(float) for c in ("open","high","low","close"))
MIN = 60_000_000_000
# 15m bars: bucket by floor(start,15min); close_time = last M1 start + 1min (partial bars possible)
bk = (T // (15*MIN))
_, first, = np.unique(bk, return_index=True)
last = np.r_[first[1:]-1, len(T)-1]
bh = np.maximum.reduceat(H, first); bl = np.minimum.reduceat(L, first)
bc = C[last]; bct = T[last] + MIN          # close = close of last M1 in bucket
# FVG on 3rd bar
rows=[]
for bull in (True, False):
    if bull: m = bl[2:] > bh[:-2]; near = bl[2:]; far = bh[:-2]
    else:    m = bh[2:] < bl[:-2]; near = bh[2:]; far = bl[:-2]
    for j in np.flatnonzero(m):
        i3 = j+2; t3 = bct[i3]
        a = np.searchsorted(T, t3, "left")  # first M1 starting at/after the close
        e = min(a+1440, len(T))
        seg = L[a:e] <= near[j] if bull else H[a:e] >= near[j]
        k = np.flatnonzero(seg)
        if not len(k) or k[0]==0: continue
        h = a+k[0]
        leg = H[a:h].max() if bull else L[a:h].min()
        dd = 1 if bull else -1
        tc = C[h]
        if not (dd*(tc-far[j])>0 and dd*(leg-tc)>0): continue
        rows.append((T[h]+MIN, dd, near[j], far[j], leg, tc))
ev = pd.DataFrame(rows, columns=["t","d","near","far","leg","tc"]).sort_values("t").reset_index(drop=True)
print("events", len(ev))
old = pd.read_pickle("ev.pkl")
print("orig events", len(old), "match decision_time set:", len(set(ev.t) & set(pd.DatetimeIndex(old.decision_time).as_unit('ns').asi8)))

def race(tn, up, dn, d, nb=16):
    """3-way: 1 target first, -1 invalidation first, 0 timeout."""
    out = np.zeros(len(tn), int); out[:] = -9
    i0 = np.searchsorted(T, tn, "left")
    k0 = np.searchsorted(bct, tn, "right")
    for r in range(len(tn)):
        if i0[r] >= len(T) or k0[r] >= len(bct): continue
        ref = O[i0[r]]; tgt = ref + d[r]*up[r]; inv = ref - d[r]*dn[r]
        ke = min(k0[r]+nb, len(bct)) - 1
        cc = bc[k0[r]:ke+1]
        bad = np.flatnonzero(cc < inv) if d[r]==1 else np.flatnonzero(cc > inv)
        tinv = bct[k0[r]+bad[0]] if len(bad) else np.iinfo(np.int64).max
        iend = np.searchsorted(T, bct[ke], "left")
        seg = H[i0[r]:iend] >= tgt if d[r]==1 else L[i0[r]:iend] <= tgt
        kk = np.flatnonzero(seg)
        thit = T[i0[r]+kk[0]]+MIN if len(kk) else np.iinfo(np.int64).max
        if thit < tinv: out[r]=1
        elif tinv < np.iinfo(np.int64).max: out[r]=-1
        else: out[r]=0
    return out
tn = ev.t.to_numpy(np.int64); d = ev.d.to_numpy()
up = d*(ev.leg-ev.tc).to_numpy(); dn = d*(ev.tc-ev.far).to_numpy()
obs = race(tn, up, dn, d)
# trailing 30-min range (known at decision) for vol matching
cm_h = pd.Series(H).rolling(30).max().to_numpy(); cm_l = pd.Series(L).rolling(30).min().to_numpy()
def trail(tn):
    i = np.searchsorted(T, tn, "left")-1
    return cm_h[i]-cm_l[i]
vol_e = trail(tn)
rng = np.random.default_rng(7)
W = 30*86400*10**9
nulls=[]; nullv=[]
for k in range(5):
    lo = np.searchsorted(T, tn-W); hi = np.searchsorted(T, tn+W)
    pick = lo + (rng.random(len(tn))*(hi-lo)).astype(int)
    rt = T[pick]  # a bar start, used as decision time (entry at that bar's open)
    nulls.append(race(rt, up, dn, d))
# vol-matched null: random time within +-30d whose trailing 30m range within +-15% of event's
for k in range(5):
    res = np.full(len(tn), -9)
    rtv = np.zeros(len(tn), np.int64)
    for r in range(len(tn)):
        lo = np.searchsorted(T, tn[r]-W); hi = np.searchsorted(T, tn[r]+W)
        for _ in range(60):
            p = lo + int(rng.random()*(hi-lo))
            v = cm_h[p-1]-cm_l[p-1]
            if abs(v-vol_e[r]) <= 0.15*vol_e[r]: break
        rtv[r] = T[p]
    nullv.append(race(rtv, up, dn, d))
np.savez("indep.npz", obs=obs, nulls=np.array(nulls), nullv=np.array(nullv), tn=tn, vol=vol_e)
def rep(name, N):
    N = np.array(N); ok = (obs!=-9) & (N!=-9).all(0)
    o = (obs[ok]==1); n = (N[:,ok]==1).mean(0)
    df = o - n
    day = pd.factorize(cl.trading_day(pd.DatetimeIndex(tn[ok]).tz_localize("UTC")))[0]
    s = np.bincount(day, df); c = np.bincount(day)
    bs = [ (s[i].sum()/c[i].sum()) for i in (rng.integers(0,len(s),len(s)) for _ in range(2000))]
    h1 = tn[ok] < pd.Timestamp("2021-01-01", tz="UTC").value
    print(name, "obs", o.mean().round(4), "null", n.mean().round(4), "diff", df.mean().round(4), np.percentile(bs,[2.5,97.5]).round(4),
          "H1", df[h1].mean().round(4), "H2", df[~h1].mean().round(4))
    print("   timeout obs", (obs[ok]==0).mean().round(3), "null", (N[:,ok]==0).mean().round(3),
          " inv obs", (obs[ok]==-1).mean().round(3), "null", (N[:,ok]==-1).mean().round(3))
    # conditional on resolved
    ro = obs[ok]; rn = N[:,ok]
    print("   P(target|resolved) obs", (ro==1).sum()/(ro!=0).sum(), "null", (rn==1).sum()/(rn!=0).sum())
rep("plain", nulls); rep("volmatched", nullv)
