"""Fit the ping-pong strategy to the trader's 4/5/6/9 Nov daily results with trading limited to the Asia session (00-08 UTC)."""
import json, sys
import numpy as np
import fit_days as fd

# target = the trader's own result on positions OPENED in the Asia session (00-08 UTC) on each day
fd.TARGET.update({"2026-11-04": 0.0, "2026-11-05": 157.0, "2026-11-06": 168.0, "2026-11-09": 587.0})
FIXED = dict(h0=0, h1=8, session_only=True, day_loss_usd=2000.0)
SPACE = dict(er_max=[0.2, 0.3, 0.4, 0.5, 0.8, 9.0], lot=[0.02, 0.04, 0.06, 0.08, 0.1, 0.15], T=[4, 5, 6, 8, 10, 12, 14, 20], G=[2, 3, 4, 5, 6, 8, 10], K=[3, 4, 5, 6, 8], flip=[True, False], pull=[0.25, 0.5, 0.75, 1.0, 1.5],
             edge=[0.5, 0.6, 0.7, 0.8], confirm=[True, False], news_flat=[True, False], eod_flat=[True, False], sides=["both", "sell"], take=[0, 1, 2, 3, 4, 6, 8],
             session_flat=[True, False], max_hold=[0, 0, 60, 120, 240])
if __name__ == "__main__":
    rng = np.random.default_rng(23); N = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    pick = lambda: {k: v[int(rng.integers(len(v)))] for k, v in SPACE.items()}
    best = None
    for _ in range(N):
        k = pick(); e, g = fd.score({**FIXED, **k})
        if best is None or e < best[0]: best = (e, k, g)
    err, kw, got = best
    for _ in range(N):                                        # hill-climb around the best
        k2 = dict(kw)
        for key in rng.choice(list(SPACE), size=int(rng.integers(1, 4)), replace=False): k2[key] = SPACE[key][int(rng.integers(len(SPACE[key])))]
        e2, g2 = fd.score({**FIXED, **k2})
        if e2 < err: err, kw, got = e2, k2, g2
    clean = {k: (v.item() if hasattr(v, "item") else v) for k, v in {**FIXED, **kw}.items()}
    json.dump(dict(err=err, kw=clean, got=got.round(2).to_dict(), target=fd.TARGET), open("fit_asia_best.json", "w"), indent=1)
    print("trader", {k[5:]: int(v) for k, v in fd.TARGET.items()}); print("fitted", {k[5:]: int(round(v)) for k, v in got.items()}, "| total abs error $", round(err)); print(clean)
