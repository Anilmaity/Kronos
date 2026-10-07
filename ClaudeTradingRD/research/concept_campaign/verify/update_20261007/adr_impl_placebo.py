import sys, runpy
g = runpy.run_path("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/update_20261007/adr_impl_rebuild.py")
globals().update(g)
import numpy as np, warnings
warnings.filterwarnings("ignore")
cap, dist, obs = evaluate(1.0)
ve = lvol[I0]
J = draw(seed=12345)
print("dist/ADR median", np.median(dist / A), "dist/ve median", np.nanmedian(dist / ve))
# P1: price-anchored levels at q * ADR from the next open (no extreme anchor, no cap), same rows, tested null
for q in (0.3, 0.5, 0.7, 0.9):
    d = q * A; lv = P0 + side * d
    o = hit(I0, NB, lv, side)
    summarise(f"P1 price+q*ADR q={q} (vol null)", o, null_rate(J, d, "vol"))
# P1b: same distances as the real caps but shuffled across rows of the same side (ADR units kept)
rng = np.random.default_rng(3)
dsh = dist.copy()
for s_ in (1, -1):
    ix = np.flatnonzero(side == s_); dsh[ix] = (dist / A)[rng.permutation(ix)] * A[ix]
o = hit(I0, NB, P0 + side * dsh, side)
summarise("P1b shuffled cap dist (ADR units), vol null", o, null_rate(J, dsh, "vol"))
# P2: price-anchored at k * local vol (units the null preserves exactly)
for k in (20, 40, 60, 80):
    d = k * ve; lv = P0 + side * d
    o = hit(I0, NB, lv, side)
    summarise(f"P2 price+k*lvol k={k} (vol null)", o, null_rate(J, d, "vol"))
# Jensen check: spread of the scaling ratio
r = lvol[np.maximum(J[:, 0], 0)] / ve
print("vn/ve ratio quantiles 5/25/50/75/95:", np.nanpercentile(r, [5, 25, 50, 75, 95]).round(3))
ra = adr_bar[np.maximum(J[:, 0], 0)] / A
print("ADRn/ADRe ratio quantiles:", np.nanpercentile(ra, [5, 25, 50, 75, 95]).round(3))
