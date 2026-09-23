"""Heavier clustering: each setup fires every minute for 120 minutes (e.g. 'in the
NY-AM killzone while above the midnight open'), random direction per setup, 1200 setups."""
import sys
from common import *
L = int(sys.argv[1]) if len(sys.argv) > 1 else 120
K = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
out = []
ny_ok = np.flatnonzero((NYMIN >= 7*60) & (NYMIN < 9*60))
for s in range(int(sys.argv[3]) if len(sys.argv) > 3 else 40):
    rng = np.random.default_rng(5000 + s)
    starts = np.sort(rng.choice(ny_ok, K, replace=False))
    pos = np.unique((starts[:, None] + np.arange(L)[None, :]).ravel())
    pos = pos[pos < len(TN)]
    sd = dict(zip(starts, rng.choice([-1, 1], len(starts))))
    owner = starts[np.searchsorted(starts, pos, side="right") - 1]
    dirs = np.array([sd[o] for o in owner])
    ev = events_from_pos(pos, dirs, 3.0, 2.0)
    r = cl.trade_test(ev, max_hold="2h", n_boot=1000, blocks=False)
    h = r["halves"]
    out.append((s, r["n"], r["diff"], r["ci_lo"], r["ci_hi"], r["ci_method"], r["mde"], r["verdict"], z(r), h["H1"]["diff"], h["H2"]["diff"]))
    print(out[-1], flush=True)
df = pd.DataFrame(out, columns="seed n diff lo hi how mde verdict z h1 h2".split())
print(df.verdict.value_counts())
print("z sd", df.z.std(), "frac |z|>1.96", (df.z.abs() > 1.96).mean())
df.to_csv(f"exp2_clustered_L{L}_K{K}.csv", index=False)
