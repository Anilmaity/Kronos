"""Deeper Asia-only fit: parallel random search, then hill-climbs from the best starts. Target = trader's Asia-entry results."""
import json, sys
from multiprocessing import Pool
import numpy as np

TARGET = {"2026-11-04": 0.0, "2026-11-05": 157.0, "2026-11-06": 168.0, "2026-11-09": 587.0}
FIXED = dict(h0=0, h1=8, session_only=True, day_loss_usd=2000.0)
SPACE = dict(er_max=[0.1, 0.12, 0.15, 0.18, 0.2, 0.25, 0.3, 0.4, 0.5, 0.8, 9.0], lot=[0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.11, 0.12, 0.13, 0.14, 0.15, 0.18], T=[3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16], G=[2, 3, 4, 5, 6, 7, 8, 9, 10, 12],
             K=[3, 4, 5, 6, 8], flip=[True, False], pull=[0.25, 0.4, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5], edge=[0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8], confirm=[True, False], news_flat=[True, False],
             eod_flat=[True], sides=["both", "sell"], take=[0, 1, 2, 3, 4, 5, 6, 8], session_flat=[True, False], max_hold=[0, 30, 60, 120, 240])
_fd = None
def score(kw):
    global _fd
    if _fd is None:
        import fit_days as fd; fd.TARGET.clear(); fd.TARGET.update(TARGET); _fd = fd
    e, g = _fd.score({**FIXED, **kw}); return e, kw, {k: float(v) for k, v in g.items()}
def climb(args):
    kw, seed, steps = args; rng = np.random.default_rng(seed); err, _, got = score(kw)
    for _ in range(steps):
        k2 = dict(kw)
        for key in rng.choice(list(SPACE), size=int(rng.integers(1, 4)), replace=False): k2[key] = SPACE[key][int(rng.integers(len(SPACE[key])))]
        e2, _, g2 = score(k2)
        if e2 < err: err, kw, got = e2, k2, g2
    return err, kw, got
if __name__ == "__main__":
    N, steps = int(sys.argv[1]), int(sys.argv[2]); rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 101)
    draws = [{k: v[int(rng.integers(len(v)))] for k, v in SPACE.items()} for _ in range(N)]
    with Pool(8) as pool:
        res = sorted(pool.map(score, draws, chunksize=50), key=lambda x: x[0])
        prev = json.load(open("fit_asia_best_v2.json"))["kw"]; res = [(0, {k: prev[k] for k in SPACE}, None)] + res   # also climb from the previous best
        starts = [(r[1], 1000 + i, steps) for i, r in enumerate(res[:8])]
        best = min(pool.map(climb, starts), key=lambda x: x[0])
    err, kw, got = best; clean = {k: (v.item() if hasattr(v, "item") else v) for k, v in {**FIXED, **kw}.items()}
    json.dump(dict(err=err, kw=clean, got=got, target=TARGET), open("fit_asia_best.json", "w"), indent=1)
    print("trader (Asia)", {k[5:]: int(v) for k, v in TARGET.items()}); print("fitted       ", {k[5:]: int(round(v)) for k, v in got.items()}, "| total abs error $", round(err)); print(clean)
