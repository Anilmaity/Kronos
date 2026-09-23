"""Independent implementation: own 1h resample, own FVG, own fill scan, own nulls (several seeds),
plus a volatility-matched null. Scratch only; nothing is written to results."""
import sys
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import numpy as np, pandas as pd
import concept_lab as cl
m1 = cl.load_m1()
idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
T = idx.as_unit("ns").asi8
O = m1.open.to_numpy(float); H = m1.high.to_numpy(float); L = m1.low.to_numpy(float)
N = len(T)
key = idx.floor("1h")
g = pd.DataFrame({"h": H, "l": L}, index=idx).groupby(key)
hb = g.h.max(); lb = g.l.min()
st = pd.DatetimeIndex(hb.index)
ct = (st + pd.Timedelta(hours=1)).as_unit("ns").asi8
h = hb.to_numpy(); l = lb.to_numpy()
# 3-bar range / ATR-ish volatility (mean 1h range of previous 20 bars) known at bar close
rng1 = h - l
vol20 = pd.Series(rng1).rolling(20).mean().to_numpy()
ev = []
for i in range(2, len(h)):
    if l[i] > h[i-2]:
        ev.append((i, 1, h[i-2]))
    elif h[i] < l[i-2]:
        ev.append((i, -1, l[i-2]))
ev = np.array(ev, dtype=object)
bi = ev[:, 0].astype(int); d = ev[:, 1].astype(int); far = ev[:, 2].astype(float)
t = ct[bi]
print("events", len(t))
# prefix min / max structures -> use sparse table style via numpy windows: do per-event scan
def hit(tstart, level, direction, horizon=1440):
    i0 = np.searchsorted(T, tstart, "left")
    out = np.zeros(len(tstart), bool)
    for k in range(len(tstart)):
        a = i0[k]; b = min(a + horizon, N)
        if b <= a: out[k] = False; continue
        if direction[k] == 1:
            out[k] = L[a:b].min() <= level[k]
        else:
            out[k] = H[a:b].max() >= level[k]
    return out, i0
obs, i0 = hit(t, far, d)
px = O[np.minimum(i0, N-1)]
dist = np.abs(px - far)
print("obs rate", obs.mean())
# candidate null moments: M1 bar starts on :00 minute
mins = ((T // 60_000_000_000) % 60)
cand = T[mins == 0]
# vol at candidate: vol20 of last closed 1h bar at candidate time
cand_bar = np.searchsorted(ct, cand, "right") - 1   # last 1h bar with close<=cand
cand_vol = np.where(cand_bar >= 0, vol20[np.maximum(cand_bar, 0)], np.nan)
cand_r3 = np.where(cand_bar >= 2, (np.maximum.reduce([h[cand_bar], h[cand_bar-1], h[cand_bar-2]]) -
                   np.minimum.reduce([l[cand_bar], l[cand_bar-1], l[cand_bar-2]])), np.nan)
ev_r3 = np.maximum.reduce([h[bi], h[bi-1], h[bi-2]]) - np.minimum.reduce([l[bi], l[bi-1], l[bi-2]])
W = 30 * 86400 * 10**9
lo = np.searchsorted(cand, t - W, "left"); hi = np.searchsorted(cand, t + W, "right")
def null_draw(seed, volmatch=False):
    r = np.random.default_rng(seed)
    tn = np.empty(len(t), np.int64)
    for k in range(len(t)):
        if volmatch:
            pool = np.arange(lo[k], hi[k])
            rr = cand_r3[pool]
            ok = np.isfinite(rr) & (np.abs(np.log(rr / ev_r3[k])) < 0.15)
            pool = pool[ok]
            if len(pool) == 0:
                pool = np.arange(lo[k], hi[k])
            tn[k] = cand[r.choice(pool)]
        else:
            tn[k] = cand[r.integers(lo[k], hi[k])]
    j0 = np.searchsorted(T, tn, "left")
    pk = O[j0]
    lvl = np.where(d == 1, pk - dist, pk + dist)
    hh, _ = hit(tn, lvl, d)
    return hh
res = {}
for vm in (False, True):
    diffs = []
    for s in range(10):
        nl = null_draw(1000 + s, vm)
        diffs.append(obs.mean() - nl.mean())
    res[vm] = diffs
    print("volmatched" if vm else "plain", "null diffs over 10 seeds: mean %.4f  sd %.4f  min %.4f max %.4f" %
          (np.mean(diffs), np.std(diffs), np.min(diffs), np.max(diffs)))
# opposite-side same-moment control (continuation level at same distance)
opp, _ = hit(t, np.where(d == 1, px + dist, px - dist), -d)
print("same-moment opposite side (continuation) level hit rate", opp.mean(), "diff far-vs-ahead", obs.mean() - opp.mean())

# CI for the vol-matched null through the harness's rate_test (not written)
nulls = np.column_stack([null_draw(2000 + s, True) for s in range(5)]).astype(float)
tt = pd.DatetimeIndex(t).tz_localize("UTC")
r = cl.rate_test(obs.astype(float), tt, available_at=tt, null=nulls, claim="+")
print({k: r.get(k) for k in ("verdict", "n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p")})
