"""Bucket check for average-daily-range u1007a: does the high-'used ADR' slice survive
bucket-matched placebos (shuffled distance within bucket, machinery bias, beyond-extreme null)?"""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/update_20261007")
from adr_u1007a_faith import events, Book, stat, hits, cl  # noqa: E402

OUT = {}
def rep(k, r):
    OUT[k] = r; print(f"{k:60s} {json.dumps(r)}", flush=True)

ev = events(14); b = Book(ev)
cap = ev["cap"].to_numpy(); dist = (cap - b.p0) * b.side
used = ((ev["hi"] - ev["lo"]) / ev["adr"]).to_numpy()
bk = np.digitize(used, [0.4, 0.6, 0.8])
H1 = np.asarray(b.t < pd.Timestamp("2021-01-01", tz="UTC"))
ny = cl.to_ny(b.t)
o, m = b.run(cap)
ob, mb = b.run(cap, beyond_only=True)
# shuffled distance within (bucket, NY hour, side, year)
codes = pd.factorize(pd.Series(list(zip(bk, ny.hour, b.side, b.t.year))))[0]
rg = np.random.default_rng(5); perm = np.arange(len(dist))
for g in np.unique(codes):
    ix = np.flatnonzero(codes == g); perm[ix] = rg.permutation(ix)
op, mp = b.run(b.p0 + b.side * dist[perm])
# machinery bias: draw-0 moment at the event distance vs draws 1-4 scaled by vn_k/vn_0
vn0 = b.vn[0]; ok0 = np.flatnonzero(np.isfinite(b.px[0]) & np.isfinite(vn0))
ps = np.full(len(cap), np.nan)
ps[ok0] = hits(b.tk[0][ok0], b.px[0][ok0] + b.side[ok0] * dist[ok0], b.side[ok0], b.nb[ok0])
m2 = np.full((len(cap), 4), np.nan)
for j, k in enumerate(range(1, 5)):
    okk = np.flatnonzero(np.isfinite(b.px[k]) & np.isfinite(vn0))
    dd = dist[okk] * b.vn[k][okk] / vn0[okk]
    m2[okk, j] = hits(b.tk[k][okk], b.px[k][okk] + b.side[okk] * dd, b.side[okk], b.nb[okk])
for i, nm in enumerate(["[0,.4)", "[.4,.6)", "[.6,.8)", "[.8,1)"]):
    s = bk == i
    r = stat(o, m, b.t, s); r["H1"] = stat(o, m, b.t, s & H1).get("diff"); r["H2"] = stat(o, m, b.t, s & ~H1).get("diff")
    rep(f"used {nm} ADR cap", r)
    rep(f"used {nm} ADR cap, beyond-extreme null", stat(ob, mb, b.t, s))
    rep(f"used {nm} shuffled-distance placebo", stat(op, mp, b.t, s))
    rep(f"used {nm} machinery bias (random moment)", stat(ps, m2, b.t, s))
    for lo_, hi_ in ((19, 24), (0, 7), (7, 12), (12, 17)):
        sel = s & np.asarray((ny.hour >= lo_) & (ny.hour < hi_))
        rep(f"used {nm} NY [{lo_},{hi_}) ADR cap", stat(o, m, b.t, sel))
json.dump(OUT, open("adr_u1007a_bucket_out.json", "w"), indent=1)
