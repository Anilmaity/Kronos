import sys, runpy
sys.argv = [sys.argv[0]] + sys.argv[1:]
g = runpy.run_path("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/update_20261007/adr_impl_rebuild.py")
globals().update(g)
import numpy as np, pandas as pd

cap, dist, obs = evaluate(1.0)
print("neg dist rows", int((dist <= 0).sum()), "obs rate by side", np.nanmean(obs[side == 1]), np.nanmean(obs[side == -1]))
ve = lvol[I0]

# 1) reproduction: plain same-clock draws, vol-scaled distance
J = draw(seed=12345)
r1 = null_rate(J, dist, "vol")
summarise("R1 repro: any null, vol-scaled", obs, r1)
J2 = draw(seed=999)
summarise("R1b repro other seed", obs, null_rate(J2, dist, "vol"))

# diagnostics: is the null level inside its own day's traded range?
jj = np.maximum(J[:, 0], 0)
lvl = O[jj] + side * dist * lvol[jj] / ve
inside = np.where(side == 1, lvl <= rhi[jj], lvl >= rlo[jj])
print("null level already inside/at its day's running range (rep0):", float(np.nanmean(inside[J[:, 0] >= 0])))
st_null = (rhi[jj] - rlo[jj]) < adr_bar[jj]
print("null moment with day range still < ADR (rep0):", float(np.nanmean(st_null[J[:, 0] >= 0])))

# 2) state-matched null: null day must also have running range < its own ADR
def acc_state(pend, cand):
    return np.isfinite(rhi[cand]) & np.isfinite(adr_bar[cand]) & ((rhi[cand] - rlo[cand]) < adr_bar[cand])
Js = draw(seed=12345, accept=acc_state)
summarise("R2 state-matched null, vol-scaled", obs, null_rate(Js, dist, "vol"))
summarise("R2b state-matched null, ADR-scaled", obs, null_rate(Js, dist, "adr"))

# 3) structural null: state-matched AND null level beyond the null day's running extreme (same side)
def acc_struct(pend, cand):
    l = O[cand] + side[pend] * dist[pend] * lvol[cand] / ve[pend]
    beyond = np.where(side[pend] == 1, l > rhi[cand], l < rlo[cand])
    return acc_state(pend, cand) & beyond & np.isfinite(l)
Jb = draw(seed=12345, accept=acc_struct)
rb = null_rate(Jb, dist, "vol")
summarise("R3 struct null: state + beyond extreme", obs, rb)
def acc_struct_adr(pend, cand):
    l = O[cand] + side[pend] * dist[pend] * adr_bar[cand] / A[pend]
    beyond = np.where(side[pend] == 1, l > rhi[cand], l < rlo[cand])
    return acc_state(pend, cand) & beyond & np.isfinite(l)
Jba = draw(seed=12345, accept=acc_struct_adr)
summarise("R3b struct null (ADR-scaled)", obs, null_rate(Jba, dist, "adr"))
def acc_beyond_only(pend, cand):
    l = O[cand] + side[pend] * dist[pend] * lvol[cand] / ve[pend]
    return np.where(side[pend] == 1, l > rhi[cand], l < rlo[cand]) & np.isfinite(l) & np.isfinite(rhi[cand])
Jbo = draw(seed=12345, accept=acc_beyond_only)
summarise("R3c beyond-extreme only (no state)", obs, null_rate(Jbo, dist, "vol"))

# 4) dose-response: fixed rows (running range < 0.5 ADR), caps at m*ADR, plain vol-scaled null (as tested)
base = (RH - RL) < 0.5 * A
print("dose-response rows", int(base.sum()))
for m in (0.5, 0.75, 1.0, 1.25, 1.5):
    c_m, d_m, o_m = evaluate(m)
    summarise(f"R4 m={m} plain null", o_m, null_rate(J, d_m, "vol"), mask=base)
for m in (0.5, 0.75, 1.0, 1.25, 1.5):
    c_m, d_m, o_m = evaluate(m)
    summarise(f"R4s m={m} struct null", o_m, null_rate(Jbo, d_m, "vol"), mask=base)

# 5) feed-regression exclusion (2019-02..2020-02) on the reproduction
dd = pd.DatetimeIndex(days[DD])
ex = ~((dd >= "2019-02-01") & (dd < "2020-03-01"))
summarise("R5 repro excl 2019-02..2020-02", obs, r1, mask=ex)
