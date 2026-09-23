"""Baseline: unclustered random books (random 5-min marks, random direction)."""
from common import *
cand = np.flatnonzero((NY.minute.to_numpy() % 5) == 0)
out = []
for b in range(150):
    rng = np.random.default_rng(20000 + b)
    pos = np.sort(rng.choice(cand, 5000, replace=False))
    ev = events_from_pos(pos, rng.choice([-1, 1], len(pos)), 3.0, 2.0)
    r = cl.trade_test(ev, max_hold="3h", n_boot=1000, blocks=False)
    out.append((b, r["diff"], r["ci_lo"], r["ci_hi"], r["p"], r["verdict"], z(r)))
df = pd.DataFrame(out, columns="b diff lo hi p verdict z".split())
print(df.verdict.value_counts()); se = (df.hi - df.lo) / 3.92
print("z mean", df.z.mean(), "z sd", df.z.std(), "frac z>1.96", (df.z > 1.96).mean(), "frac |z|>1.96", (df.z.abs() > 1.96).mean())
df.to_csv("exp10_unclustered.csv", index=False)
