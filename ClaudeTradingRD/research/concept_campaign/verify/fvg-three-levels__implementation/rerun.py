import sys, importlib.util, time
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03a")
spec = importlib.util.spec_from_file_location("fv3", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03a/fvg-three-levels.py")
fv3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(fv3)
cl = fv3.cl
t0=time.time()
m1 = cl.load_m1()
ev = fv3.detect(m1)
ev.to_pickle("ev.pkl")
print(len(ev), time.time()-t0)
b15 = cl.bars("15min")
t = pd.DatetimeIndex(ev["decision_time"]); d = ev["direction"].to_numpy()
up = d*(ev.leg_extreme.to_numpy()-ev.touch_close.to_numpy()); dn = d*(ev.touch_close.to_numpy()-ev.far_edge.to_numpy())
obs = fv3.race(t, up, dn, d, b15=b15)
out = {"obs": obs}
for name, kw in [("plain", {}), ("tod30", {"tod_tol_min": 30})]:
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, **kw)
    nl = np.column_stack([fv3.race(pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"), up, dn, d, b15=b15) for k in range(5)])
    out[name] = nl
    np.save(f"null_{name}.npy", nl)
    m = np.nanmean(nl, axis=1)
    ok = ~np.isnan(obs) & ~np.isnan(m)
    df = obs[ok]-m[ok]
    # day-block bootstrap
    day = cl.trading_day(t[ok]); codes = pd.factorize(day)[0]
    sums = np.bincount(codes, df); cnt = np.bincount(codes)
    rng = np.random.default_rng(1); bs=[]
    for _ in range(2000):
        s = rng.integers(0, len(sums), len(sums)); bs.append(sums[s].sum()/cnt[s].sum())
    h1 = t[ok] < pd.Timestamp("2021-01-01", tz="UTC")
    print(name, "obs", np.nanmean(obs[ok]).round(4), "null", np.nanmean(m[ok]).round(4), "diff", df.mean().round(4),
          np.percentile(bs,[2.5,97.5]).round(4), "H1", df[h1].mean().round(4), "H2", df[~h1].mean().round(4), "n", ok.sum())
np.save("obs.npy", obs)
