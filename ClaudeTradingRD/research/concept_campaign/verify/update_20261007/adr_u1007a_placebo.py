"""Placebo controls for average-daily-range u1007a: same null machinery, ADR removed.

P1 shuffled distance: each row's cap distance from price is swapped with another row's
   (same NY hour, same side, same calendar month), so the level has the same distance
   distribution but no relation to today's ADR or extremes.
P2 stale ADR: cap built from the ADR as of 40 real trading days earlier (still a level
   beyond today's extreme, same structure, wrong ADR).
P3 unscaled null: null distance NOT vol-scaled (raw points), to show how much the vol
   ratio drives the null rate.
P4 null-vs-null: draw 0 of the null (a random matched moment, its own vol-scaled level)
   scored as if observed against draws 1-4 - a pure machinery check, ADR-free.
"""
import sys
import json

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/update_20261007")
from adr_u1007a_faith import events, Book, stat, hits, lvol, mkt, REAL, RCT, D, cl  # noqa: E402

OUT = {}


def rep(name, r):
    OUT[name] = r
    print(f"{name:55s} {json.dumps(r)}", flush=True)


ev = events(14)
b = Book(ev)
cap = ev["cap"].to_numpy()
dist = (cap - b.p0) * b.side
H1 = np.asarray(b.t < pd.Timestamp("2021-01-01", tz="UTC"))

# P1 shuffled distances
ny = cl.to_ny(b.t)
grp = pd.Series(list(zip(ny.hour, b.side, b.t.year, b.t.month)))
codes = pd.factorize(grp)[0]
rg = np.random.default_rng(11)
for rep_i in range(3):
    perm = np.arange(len(dist))
    for g in np.unique(codes):
        ix = np.flatnonzero(codes == g)
        perm[ix] = rg.permutation(ix)
    lvl = b.p0 + b.side * dist[perm]
    o, m = b.run(lvl)
    r = stat(o, m, b.t)
    r["H1"] = stat(o, m, b.t, H1).get("diff"); r["H2"] = stat(o, m, b.t, ~H1).get("diff")
    rep(f"P1 shuffled-distance placebo #{rep_i}", r)

# P2 stale ADR (40 real days earlier)
adr = (REAL["high"] - REAL["low"]).rolling(14, min_periods=14).mean().to_numpy()
pos = np.searchsorted(RCT, cl.data.utc_ns(b.t), side="right") - 1 - 40
stale = np.where(pos >= 0, adr[np.clip(pos, 0, None)], np.nan)
ok = (ev["hi"] - ev["lo"]).to_numpy() < stale
lvl = np.where(b.side == 1, ev["lo"] + stale, ev["hi"] - stale)
lvl = np.where(ok, lvl, np.nan)
o, m = b.run(lvl)
r = stat(o, m, b.t, ok)
r["H1"] = stat(o, m, b.t, ok & H1).get("diff"); r["H2"] = stat(o, m, b.t, ok & ~H1).get("diff")
rep("P2 stale ADR (t-40 real days) caps", r)

# P3 unscaled null (raw-point distance)
ve_save = b.ve.copy()
vn_save = [v.copy() for v in b.vn]
b.ve = np.ones_like(b.ve); b.vn = [np.ones_like(v) for v in b.vn]
o, m = b.run(cap)
rep("P3 null without vol scaling", stat(o, m, b.t))
b.ve = ve_save; b.vn = vn_save

# P4 null-vs-null: pseudo-observed = null draw 0 (its own matched moment + vol-scaled level)
o_full, m_full = b.run(cap)
pseudo = m_full[:, 0]
rest = m_full[:, 1:]
r = stat(pseudo, rest, b.t)
rep("P4 null draw0 vs draws1-4 (machinery only)", r)
# P4b: pseudo-observed at the draw-0 moment, level at UNSCALED event distance, vs draws 1-4
#      scaled by vn_k / vn_0 -> isolates the Jensen effect of a noisy vol ratio
tk0, px0, vn0 = b.tk[0], b.px[0], b.vn[0]
ok0 = np.flatnonzero(np.isfinite(px0) & np.isfinite(vn0))
pseudo2 = np.full(len(cap), np.nan)
pseudo2[ok0] = hits(tk0[ok0], px0[ok0] + b.side[ok0] * dist[ok0], b.side[ok0], b.nb[ok0])
mat2 = np.full((len(cap), 4), np.nan)
for j, k in enumerate(range(1, 5)):
    tk, px, vn = b.tk[k], b.px[k], b.vn[k]
    okk = np.flatnonzero(np.isfinite(px) & np.isfinite(vn0))
    dd = dist[okk] * vn[okk] / vn0[okk]
    mat2[okk, j] = hits(tk[okk], px[okk] + b.side[okk] * dd, b.side[okk], b.nb[okk])
rep("P4b random moment (event dist) vs vol-scaled nulls", stat(pseudo2, mat2, b.t))

json.dump(OUT, open("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/update_20261007/adr_u1007a_placebo_out.json", "w"), indent=1)
