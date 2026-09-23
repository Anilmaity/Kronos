import sys
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import numpy as np, pandas as pd
import concept_lab as cl
m1 = cl.load_m1()
mkt = cl.get_market()
b = cl.bars("1h")
h, l = b.high.to_numpy(float), b.low.to_numpy(float)
c = b.close.to_numpy(float)
n = len(h)
bull = np.zeros(n, bool); bear = np.zeros(n, bool)
bull[2:] = l[2:] > h[:-2]; bear[2:] = h[2:] < l[:-2]
sel = bull | bear
t = pd.DatetimeIndex(b.close_time)[sel]
up = bull[sel]
far = np.where(bull, np.r_[np.nan, np.nan, h[:-2]], np.r_[np.nan, np.nan, l[:-2]])[sel]
near = np.where(bull, l, h)[sel]
cl3 = c[sel]
print("n events", len(t))
pos = mkt.pos_at_or_after(t)
px = mkt.o[np.minimum(pos, len(mkt.o)-1)]
gapmin = (mkt.tn[np.minimum(pos, len(mkt.tn)-1)].astype("int64") - t.as_unit("ns").asi8)/6e10
wrong = np.where(up, px <= far, px >= far)
print("first bar starts >1 min after decision (halt/weekend):", (gapmin > 0).sum())
print("px already at/through far edge at start:", wrong.sum())
dist = np.abs(px - far)
def fill(times, level, upm):
    out = np.full(len(times), np.nan)
    for side, s in (("below", upm), ("above", ~upm)):
        if s.any():
            out[s] = cl.touch(times[s], level[s], side, horizon_bars=1440)["hit"].to_numpy()
    return out
obs = fill(t, far, up)
rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)
nulls = []
for k in range(5):
    tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
    ok = ~tk.isna()
    out = np.full(len(t), np.nan)
    pk = mkt.o[mkt.pos_at_or_after(tk[ok])]
    lvl = np.where(up[ok], pk - dist[ok], pk + dist[ok])
    out[ok] = fill(tk[ok], lvl, up[ok])
    nulls.append(out)
nul = np.nanmean(np.vstack(nulls), axis=0)
print("obs", np.nanmean(obs), "null", np.nanmean(nul), "diff", np.nanmean(obs - nul))
for name, m in [("gap-start events", gapmin > 0), ("contiguous", gapmin == 0), ("wrong-side", wrong), ("not wrong-side", ~wrong)]:
    print(name, m.sum(), "obs", np.nanmean(obs[m]), "null", np.nanmean(nul[m]), "diff", np.nanmean((obs-nul)[m]))
# a single-rep paired diff from the gap: contribution
print("contribution of wrong-side rows to total diff:", np.nansum((obs-nul)[wrong]) / len(t))
np.savez("diag.npz", obs=obs, nul=nul, wrong=wrong, gapmin=gapmin, t=t.asi8, up=up, dist=dist, px=px, far=far)
