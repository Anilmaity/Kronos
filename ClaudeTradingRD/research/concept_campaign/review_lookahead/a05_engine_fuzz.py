"""Brute-force M1 walk vs the vectorised resolver on adversarial ranges: i0 on/around
64-bar block edges, 1-bar holds, very long holds, i1 == N (end of data), NaN targets,
thresholds equal to bar extremes (tie semantics)."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import concept_lab as cl
from concept_lab.engine import resolve_trades
mk = cl.get_market(); N = len(mk.o)
rng = np.random.default_rng(7)
def brute(L, s, t, a, b):
    for k in range(a, b):
        hs = mk.l[k] <= s if L else mk.h[k] >= s
        ht = (not np.isnan(t)) and (mk.h[k] >= t if L else mk.l[k] <= t)
        if hs:
            return k, (min(s, mk.o[k]) if L else max(s, mk.o[k])), 0
        if ht:
            return k, t, 1
    return b - 1, mk.c[b - 1], 2
M = 6000
i0 = np.concatenate([rng.integers(0, N - 5, M // 3),
                     (rng.integers(1, N // 64 - 2, M // 3) * 64 + rng.integers(-2, 3, M // 3)),
                     N - rng.integers(2, 400, M - 2 * (M // 3))])
hold = np.where(rng.random(M) < 0.2, 1, rng.integers(1, 20000, M))
hold[:50] = 200000
i1 = np.minimum(i0 + hold, N)
L = rng.random(M) < 0.5
e = mk.o[i0]
dist = rng.uniform(0.05, 30, M)
stop = np.where(L, e - dist, e + dist)
tgt = np.where(L, e + dist * rng.uniform(0.2, 4, M), e - dist * rng.uniform(0.2, 4, M))
tgt[rng.random(M) < 0.1] = np.nan
# exact-equality thresholds: target == some future bar high / stop == some future low
j = np.minimum(i0 + rng.integers(0, 50, M), i1 - 1)
eq = rng.random(M) < 0.15
tgt = np.where(eq & L, np.maximum(mk.h[j], e + 0.01), tgt)
stop = np.where(eq & ~L, np.maximum(mk.h[j], e + 0.01), stop)
r = resolve_trades(mk, L, stop, tgt, i0, i1)
bad = 0
for k in range(M):
    bp, bx, br = brute(L[k], stop[k], tgt[k], i0[k], i1[k])
    if (bp, br) != (r["exit_pos"][k], r["reason"][k]) or not np.isclose(bx, r["exit_px"][k]):
        bad += 1
        if bad < 5: print("MISMATCH", k, i0[k], i1[k], (bp, bx, br), (r["exit_pos"][k], r["exit_px"][k], r["reason"][k]))
print(f"{M} trades, mismatches: {bad}")
