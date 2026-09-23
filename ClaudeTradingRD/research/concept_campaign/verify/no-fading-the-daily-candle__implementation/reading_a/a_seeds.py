"""Reading a: own M1 resolver + own 15m-grid matched control (same dir, stop dist, +-30d), per seed."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
seed = int(sys.argv[1])
m1 = cl.load_m1(); idx = m1.index.tz_convert("UTC"); st = idx.asi8
O,H,L,C = (m1[k].to_numpy(float) for k in ("open","high","low","close"))
def resolve(ent_pos, d, stop, hold_ns=150*60_000_000_000, cost=0.04):
    out = np.full(len(ent_pos), np.nan)
    for i,(p,dd,s) in enumerate(zip(ent_pos,d,stop)):
        if p >= len(O): continue
        e = O[p]; risk = (e - s)*dd
        if not risk > 0: continue
        tgt = e + dd*2*risk
        end = np.searchsorted(st, st[p] + hold_ns, side="left")
        if end <= p: continue
        h, l = H[p:end], L[p:end]
        if dd > 0: hs = l <= s; ht = h >= tgt
        else: hs = h >= s; ht = l <= tgt
        js = np.argmax(hs) if hs.any() else 10**9; jt = np.argmax(ht) if ht.any() else 10**9
        if js == 10**9 and jt == 10**9: r = (C[end-1]-e)*dd/risk
        elif js <= jt:
            px = s if (O[p+js]-s)*dd > 0 else O[p+js]
            r = (px-e)*dd/risk
        else: r = 2.0
        out[i] = r - cost
    return out
ev = pd.read_pickle("a_indep_events.pkl")
dt = pd.DatetimeIndex(ev.decision_time).tz_convert("UTC").asi8
ent = np.searchsorted(st, dt, side="left"); d = ev.direction.to_numpy(); s = ev.stop_px.to_numpy()
R = ev.R.to_numpy(); ok = ~np.isnan(R); g = ev.my_gate.to_numpy()
grid = np.where((idx.minute % 15) == 0)[0]; gst = st[grid]
rng = np.random.default_rng(seed)
dist = np.abs(O[np.minimum(ent,len(O)-1)] - s); CR = np.full(len(ev), np.nan)
for i in np.where(ok)[0]:
    t0 = st[ent[i]]
    a = np.searchsorted(gst, t0 - 30*86400*10**9); b = np.searchsorted(gst, t0 + 30*86400*10**9)
    ps = grid[rng.integers(a, max(a+1,b-10), 5)]
    CR[i] = np.nanmean(resolve(ps, [d[i]]*5, O[ps] - d[i]*dist[i]))
np.save(f"a_cr_{seed}.npy", CR)
v = ok & ~np.isnan(CR); adj = R - CR
print(seed, "ctrl g", round(np.nanmean(CR[g&v]),4), "ctrl c", round(np.nanmean(CR[~g&v]),4), "adj diff", round(np.nanmean(adj[g&v])-np.nanmean(adj[~g&v]),4))
