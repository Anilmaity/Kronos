"""Stop-first same-bar ties vs volatility selection. Events fire right after a large
M1 bar (known at its close: decision = next bar start), RANDOM direction, tight stop.
No information in direction -> a fair harness should give diff ~ 0."""
from common import *
rng_all = (MKT.h - MKT.l) if hasattr(MKT, "h") else None
h = M1["high"].to_numpy(); l = M1["low"].to_numpy()
rg = h - l
# the bar at pos-1 was large (>= its 99th pct); decision at start of bar pos (= its close)
thr = np.nanpercentile(rg, 99)
cand = np.flatnonzero(rg[:-1] >= thr) + 1
# same TOD not required; random direction
out = []
for stop in (0.3, 0.5, 1.0, 2.0):
    for s in range(3):
        rng = np.random.default_rng(s)
        pos = np.sort(rng.choice(cand, min(8000, len(cand)), replace=False))
        ev = events_from_pos(pos, rng.choice([-1, 1], len(pos)), stop, 1.0)
        r = cl.trade_test(ev, max_hold="1h", n_boot=1000, blocks=False, seed=100 + s)
        out.append((stop, s, r["n"], round(r["diff"], 4), round(r["ci_lo"], 4), round(r["ci_hi"], 4),
                    r["verdict"], "claim-:", cl.trade_test(ev, max_hold="1h", n_boot=1000, blocks=False, seed=100 + s, claim="-")["verdict"],
                    r["exit_mix"], r["control"]["exit_mix"], round(r["avg_R_gross"], 4), round(r["control"]["avg_R_gross"], 4)))
        print(out[-1], flush=True)
