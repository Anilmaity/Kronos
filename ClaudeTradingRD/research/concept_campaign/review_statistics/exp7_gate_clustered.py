"""gate_test with a noise gate on a clustered noise baseline: each setup fires every
minute for 60 min in one random direction; the gate switches whole setups on/off at
random (like 'setup formed on a Monday' / 'HTF bias agreed'). Known at decision time."""
import sys
from common import *
NS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
L, K = 60, 1500
ny_ok = np.flatnonzero((NY.minute.to_numpy() == 0))
out = []
for s in range(NS):
    rng = np.random.default_rng(3000 + s)
    starts = np.sort(rng.choice(ny_ok, K, replace=False))
    pos = (starts[:, None] + np.arange(L)[None, :]).ravel()
    own = np.repeat(np.arange(K), L)
    keep = np.r_[True, np.diff(pos) > 0] & (pos < len(TN))
    pos, own = pos[keep], own[keep]
    dirs = rng.choice([-1, 1], K)[own]
    gate = (rng.random(K) < 0.4)[own]
    ev = events_from_pos(pos, dirs, 3.0, 2.0)
    r = cl.gate_test(ev, gate, mask_available_at=ev["decision_time"], max_hold="2h", n_boot=1000, blocks=False)
    out.append((s, r["n"], r["n_complement"], r["diff"], r["ci_lo"], r["ci_hi"], r["ci_method"], r["mde"], r["verdict"], z(r)))
    print(out[-1], flush=True)
df = pd.DataFrame(out, columns="seed ng nc diff lo hi how mde verdict z".split())
print(df.verdict.value_counts())
se = (df.hi - df.lo) / 3.92
print("frac |z|>1.96", (df.z.abs() > 1.96).mean(), "emp sd/rep se", df['diff'].std() / se.mean())
df.to_csv("exp7_gate_clustered.csv", index=False)
