"""Clustered random books: each 'setup' fires on 30 consecutive M1 minutes with one
random direction (like 'long while price sits in the zone'). No information at all."""
from common import *
out = []
ny_ok = np.flatnonzero((NYMIN >= 8*60) & (NYMIN < 11*60))
for s in range(40):
    rng = np.random.default_rng(1000 + s)
    starts = np.sort(rng.choice(ny_ok, 300, replace=False))
    pos = (starts[:, None] + np.arange(30)[None, :]).ravel()
    pos = pos[pos < len(TN)]
    dirs = np.repeat(rng.choice([-1, 1], len(starts)), 30)[:len(pos)]
    ev = events_from_pos(pos, dirs, 3.0, 2.0)
    t0 = time.time()
    r = cl.trade_test(ev, max_hold="2h", n_boot=1000, blocks=False)
    out.append((s, r["n"], r["diff"], r["ci_lo"], r["ci_hi"], r["ci_method"], r["verdict"], z(r)))
    print(out[-1], round(time.time()-t0,1), flush=True)
df = pd.DataFrame(out, columns="seed n diff lo hi how verdict z".split())
print(df.verdict.value_counts())
print("z sd", df.z.std(), "frac |z|>1.96", (df.z.abs() > 1.96).mean())
df.to_csv("exp1_clustered.csv", index=False)
