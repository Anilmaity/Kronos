import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
exec(open("indep.py").read().split("def resolve")[0].split("ev = pd.read_pickle")[0])
seed = int(sys.argv[1])
m1 = cl.load_m1(); idx = m1.index.tz_convert("UTC"); st = idx.asi8
O,H,L,C = (m1[k].to_numpy(float) for k in ("open","high","low","close"))
src = open("indep.py").read(); exec("def resolve" + src.split("def resolve")[1].split("ent = np.searchsorted")[0])
ev = pd.read_pickle("indep_events.pkl")
dt = pd.DatetimeIndex(ev.decision_time).tz_convert("UTC").asi8
ent = np.searchsorted(st, dt, side="left"); d = ev.direction.to_numpy(); s = ev.stop_px.to_numpy()
R = ev.R.to_numpy(); ok = ~np.isnan(R); g = ev.my_gate.to_numpy()
grid = np.where((idx.minute % 15) == 0)[0]
rng = np.random.default_rng(seed)
dist = np.abs(O[np.minimum(ent,len(O)-1)] - s); CR = np.full(len(ev), np.nan)
for i in np.where(ok)[0]:
    lo = np.searchsorted(grid, ent[i] - 0) ; t0 = st[ent[i]]
    a = np.searchsorted(st[grid], t0 - 30*86400*10**9); b = np.searchsorted(st[grid], t0 + 30*86400*10**9)
    ps = grid[rng.integers(a, max(a+1,b-10), 5)]
    CR[i] = np.nanmean(resolve(ps, [d[i]]*5, O[ps] - d[i]*dist[i]))
v = ok & ~np.isnan(CR); adj = R - CR
np.save(f"cr_{seed}.npy", CR); print(seed, "ctrl g", round(np.nanmean(CR[g&v]),4), "ctrl c", round(np.nanmean(CR[~g&v]),4), "adj diff", round(np.nanmean(adj[g&v])-np.nanmean(adj[~g&v]),4))
