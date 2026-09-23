"""Step 1: reproduce the campaign rate (obs 0.3981, null 0.3885) with the vectorised
simulator, and cache per-event arrays for the other steps."""
import time
import numpy as np
import pandas as pd
from sim import cl, simulate, pos, market

OUT = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/deepdive/fvg-three-levels/"
ev = pd.read_pickle("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/"
                    "fvg-three-levels__faithfulness/ev.pkl")
assert len(ev) == 34790
t = pd.DatetimeIndex(ev["decision_time"])
d = ev["direction"].to_numpy()
up = d * (ev["leg_extreme"].to_numpy() - ev["touch_close"].to_numpy())
dn = d * (ev["touch_close"].to_numpy() - ev["far_edge"].to_numpy())
market()
t0 = time.time()
obs = simulate(pos(t), d, up, dn)
print("sim secs", round(time.time() - t0, 1))
print("obs hit", np.nanmean(obs["hit"]), "n", np.isfinite(obs["hit"]).sum(), "ties", np.nanmean(obs["tie"]))

rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)
nul = []
for k in range(5):
    tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
    nul.append(simulate(pos(tk), d, up, dn))
nh = np.nanmean(np.vstack([x["hit"] for x in nul]), 0)
print("null hit", np.nanmean(nh), "ties", np.nanmean(np.vstack([x["tie"] for x in nul])))
pd.to_pickle({"ev": ev, "up": up, "dn": dn, "obs": obs, "null_base": nul, "rt_base": rt}, OUT + "s1.pkl")
