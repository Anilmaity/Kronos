"""Fit the ping-pong strategy to the XM Real trader's own daily results on 2026-11-04 / 05 / 06 / 09 (operator's goal).
This is a deliberate in-sample fit to four days; the last section shows what the fitted settings do everywhere else."""
import json, sys
import numpy as np, pandas as pd
from data import load_m1
from range_scalp import prep
import ping_pong as pp

TARGET = {"2026-11-04": -28.0, "2026-11-05": 1191.0, "2026-11-06": 473.0, "2026-11-09": 1187.0}   # trader's net by the day a position was opened
full = prep(load_m1()); w = full[(full.index >= pd.Timestamp("2026-11-03 22:00", tz="UTC")) & (full.index < pd.Timestamp("2026-11-10 12:00", tz="UTC"))]

def by_open_day(t):
    return t.groupby("day").pnl.sum().reindex(TARGET.keys()).fillna(0.0) if len(t) else pd.Series(0.0, index=TARGET.keys())

def score(kw):
    t, _ = pp.run(w, pp.P(stop=False, day_floor=-1e9, **kw)); got = by_open_day(t)
    return float(sum(abs(got[k] - v) for k, v in TARGET.items())), got

SPACE = dict(lot=[0.04, 0.08], T=[5, 7, 9, 11, 12, 14, 20], G=[2, 3, 4, 5, 6, 8], K=[3, 4, 5, 6, 8], flip=[True, False], er_max=[0.3, 0.5, 0.8, 9.0], pull=[0.5, 0.75, 1.0, 1.5],
             edge=[0.5, 0.6, 0.7, 0.8], confirm=[True, False], news_flat=[True, False], eod_flat=[True, False], sides=["both", "sell", "buy"], take=[0, 2, 3, 4, 6, 8], h0=[0, 2, 4, 10], h1=[17, 19, 21, 24])
def draw(rng): return {k: (v[int(rng.integers(len(v)))]) for k, v in SPACE.items()}

if __name__ == "__main__":
    rng = np.random.default_rng(11); N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000; seen = []
    if len(sys.argv) > 2: SPACE["sides"] = sys.argv[2].split(",")       # e.g. both,sell to keep the trader's own side mix
    for n in range(N):
        kw = draw(rng); err, got = score(kw); seen.append((err, kw, got))
    seen.sort(key=lambda x: x[0]); err, kw, got = seen[0]
    for n in range(N // 2):                                   # hill-climb: change one or two settings of the best so far
        k2 = dict(kw)
        for key in rng.choice(list(SPACE), size=int(rng.integers(1, 3)), replace=False): k2[key] = SPACE[key][int(rng.integers(len(SPACE[key])))]
        e2, g2 = score(k2)
        if e2 < err: err, kw, got = e2, k2, g2
    clean = {k: (v.item() if hasattr(v, "item") else v) for k, v in kw.items()}
    json.dump(dict(err=err, kw=clean, got=got.round(2).to_dict(), target=TARGET), open("fit_days_best.json", "w"), indent=1)
    print("target", {k[5:]: int(v) for k, v in TARGET.items()}); print("fitted", {k[5:]: int(round(v)) for k, v in got.items()}, "| total abs error $", round(err)); print(clean)
