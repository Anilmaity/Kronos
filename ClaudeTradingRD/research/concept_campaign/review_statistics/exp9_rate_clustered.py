"""rate_test when the outcome is a per-DAY fact but the book has one row per 15-min
mark of that day (e.g. 'daily high forms after the NY open' scored at every M15 bar,
or 'the level is swept today' asked every bar). Outcomes are pure coin flips with the
known null probability, so every non-NULL verdict is a false positive."""
from common import *
t_utc = pd.DatetimeIndex(pd.to_datetime(TN).tz_localize("UTC"))
td = np.asarray(cl.trading_day(t_utc))
grid = np.flatnonzero((NY.minute.to_numpy() % 15) == 0)
days_u, day_idx = np.unique(td[grid], return_inverse=True)
times = t_utc[grid]
out = []
for s in range(100):
    rng = np.random.default_rng(s)
    pick = rng.random(len(days_u)) < 0.6
    sel = pick[day_idx]
    obs = (rng.random(len(days_u)) < 0.4)[day_idx][sel].astype(float)
    tt = times[sel]
    r = cl.rate_test(obs, tt, available_at=tt, null_p=np.full(len(obs), 0.4), n_boot=1000, blocks=False)
    out.append((s, r["n"], r["diff"], r["ci_lo"], r["ci_hi"], r["ci_method"], r["verdict"], z(r)))
df = pd.DataFrame(out, columns="seed n diff lo hi how verdict z".split())
print(df.head(3))
print(df.verdict.value_counts())
se = (df.hi - df.lo) / 3.92
print("frac |z|>1.96", (df.z.abs() > 1.96).mean(), "emp sd/rep se", df['diff'].std() / se.mean())
df.to_csv("exp9_rate_clustered.csv", index=False)
