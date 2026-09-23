import numpy as np, pandas as pd
tr = pd.read_pickle("trades_b.pkl")
h = pd.DatetimeIndex(tr.decision_time).tz_convert("America/New_York").hour.to_numpy()
adj = (tr.net_R - tr.ctrl_mean_R).to_numpy(); gate = tr.gate.to_numpy().astype(bool)
print("complement share by NY hour:"); print(pd.Series(~gate).groupby(h).mean().round(2).to_dict())
print("adj mean by hour:"); print(pd.Series(adj).groupby(h).mean().round(3).to_dict())
obs = adj[gate].mean() - adj[~gate].mean()
# within-hour stratified diff (weights = complement counts)
df = pd.DataFrame({"h": h, "a": adj, "g": gate})
s = df.groupby(["h", "g"]).a.agg(["mean", "size"]).unstack()
s = s.dropna(); w = s[("size", False)]
strat = ((s[("mean", True)] - s[("mean", False)]) * w).sum() / w.sum()
print("raw diff %.4f  hour-stratified diff %.4f" % (obs, strat))
rng = np.random.default_rng(7); rate = pd.Series(gate).groupby(h).mean().reindex(h).to_numpy(); ds = []
for _ in range(2000):
    m = rng.random(len(h)) < rate; ds.append(adj[m].mean() - adj[~m].mean())
ds = np.array(ds); print("hour-matched random-mask placebo: mean %.4f sd %.4f frac>=obs %.3f" % (ds.mean(), ds.std(), (ds >= obs).mean()))
# day-block bootstrap of stratified diff
day = pd.DatetimeIndex(tr.decision_time).tz_convert("America/New_York").normalize()
df["d"] = day; days = df.d.unique(); grp = {d: i for i, d in enumerate(days)}; df["di"] = df.d.map(grp)
idx_by_day = df.groupby("di").indices; bs = []
for _ in range(500):
    pick = rng.integers(0, len(days), len(days)); ii = np.concatenate([idx_by_day[p] for p in pick]); x = df.iloc[ii]
    s = x.groupby(["h", "g"]).a.agg(["mean", "size"]).unstack().dropna(); w = s[("size", False)]
    bs.append(((s[("mean", True)] - s[("mean", False)]) * w).sum() / w.sum())
print("stratified day-bootstrap 95%% CI [%.4f, %.4f]" % tuple(np.percentile(bs, [2.5, 97.5])))
