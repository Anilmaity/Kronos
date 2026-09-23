"""Forking paths: a pure-noise book re-run with different `seed` (and other free knobs).
write_result accepts any of them; how many noise books can be pushed to EDGE?"""
from common import *
cand = np.flatnonzero((NY.minute.to_numpy() % 5) == 0)
res = []
for b in range(20):
    rng = np.random.default_rng(777 + b)
    pos = np.sort(rng.choice(cand, 4000, replace=False))
    ev = events_from_pos(pos, rng.choice([-1, 1], len(pos)), 3.0, 2.0)
    vs = []
    for sd in range(20):
        r = cl.trade_test(ev, max_hold="3h", n_boot=1000, blocks=False, seed=sd)
        vs.append(r["verdict"])
    dflt = cl.trade_test(ev, max_hold="3h", n_boot=1000, blocks=False)["verdict"]
    res.append((b, dflt, vs.count("EDGE"), vs.count("NEGATIVE"), vs.count("NULL"), vs.count("UNDERPOWERED")))
    print(res[-1], flush=True)
df = pd.DataFrame(res, columns="book default_verdict n_edge_of20seeds n_neg n_null n_under".split())
print(df)
print("books with >=1 EDGE among 20 seeds:", (df.n_edge_of20seeds > 0).sum(), "/", len(df),
      " default EDGE:", (df.default_verdict == "EDGE").sum())
df.to_csv("exp5_seed_shopping.csv", index=False)
