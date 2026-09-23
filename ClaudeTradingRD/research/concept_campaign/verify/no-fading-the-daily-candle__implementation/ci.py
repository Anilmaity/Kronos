import numpy as np, pandas as pd
ev = pd.read_pickle("indep_events.pkl"); R = ev.R.to_numpy(); g = ev.my_gate.to_numpy()
CR = np.nanmean(np.vstack([np.load(f"cr_{s}.npy") for s in range(1,7)]), 0)
v = ~np.isnan(R) & ~np.isnan(CR)
day = pd.DatetimeIndex(ev.decision_time).tz_convert("America/New_York").tz_localize(None)
day = (day + pd.Timedelta(hours=6)).normalize()
rng = np.random.default_rng(0)
def stat(adj, sel):
    df = pd.DataFrame({"a": adj, "g": g, "day": day})[sel]
    agg = df.groupby("day").apply(lambda x: pd.Series({"sg": x.a[x.g].sum(), "ng": x.g.sum(), "sc": x.a[~x.g].sum(), "nc": (~x.g).sum()})).to_numpy()
    point = agg[:,0].sum()/agg[:,1].sum() - agg[:,2].sum()/agg[:,3].sum()
    n = len(agg); bs = []
    for b in range(2000):   # stationary block bootstrap over days, mean block 2 days
        idx = []; i = rng.integers(n)
        while len(idx) < n:
            idx.append(i); i = (i+1) % n if rng.random() > 0.5 else rng.integers(n)
        k = agg[idx].sum(0); bs.append(k[0]/k[1]-k[2]/k[3])
    return point, np.percentile(bs, [2.5, 97.5])
yrs = pd.DatetimeIndex(ev.decision_time).year
for lab, sel in (("all", v), ("H1", v & (yrs < 2021)), ("H2", v & (yrs >= 2021))):
    print(lab, "adj(30-draw ctrl)", stat(R - CR, sel), "raw", stat(R, sel)[0])
print("ctrl gated", CR[g&v].mean(), "ctrl compl", CR[~g&v].mean())
