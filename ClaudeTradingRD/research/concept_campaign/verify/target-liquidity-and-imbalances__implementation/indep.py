"""Independent re-implementation of reading b (no harness test calls; only load_m1 for data)."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
m1 = cl.load_m1()
idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
H, L, O = m1.high.to_numpy(float), m1.low.to_numpy(float), m1.open.to_numpy(float)
tn = idx.asi8
N = len(tn); HZ = 240
# 15m bars (UTC resample, left label), close = start + 15m
b = m1[["open","high","low","close"]].resample("15min", label="left", closed="left").agg(
    {"open":"first","high":"max","low":"min","close":"last"}).dropna()
ct = b.index + pd.Timedelta("15min")
h, l, c = b.high.to_numpy(), b.low.to_numpy(), b.close.to_numpy()
pc = np.r_[np.nan, c[:-1]]
tr = np.nanmax(np.vstack([h-l, abs(h-pc), abs(l-pc)]), 0)
atr = pd.Series(tr).rolling(14, min_periods=14).mean().to_numpy()
bull = np.r_[False, False, l[2:] > h[:-2]]
bear = np.r_[False, False, h[2:] < l[:-2]]
fin = np.isfinite(atr)
# start M1 index for every bar close
i0 = np.searchsorted(tn, ct.asi8, "left")
valid = i0 < N
# forward rolling min low / max high over next 240 M1 bars starting at i0
from numpy.lib.stride_tricks import sliding_window_view as swv
Lp = np.r_[L, np.full(HZ, np.inf)]; Hp = np.r_[H, np.full(HZ, -np.inf)]
fmin = swv(Lp, HZ).min(1)[:N]; fmax = swv(Hp, HZ).max(1)[:N]
def hit_below(i, lev): return fmin[np.minimum(i, N-1)] <= lev
def hit_above(i, lev): return fmax[np.minimum(i, N-1)] >= lev
px0 = O[np.minimum(i0, N-1)]
# own-bar extremes for EVERY bar: low (below side) and high (above side)
hitL = hit_below(i0, l); hitH = hit_above(i0, h)
dL = (px0 - l)/atr; dH = (h - px0)/atr     # distance in ATR (positive = level beyond price)
ev = (bull | bear) & fin & valid
print("events", ev.sum(), "bull", (bull&ev).sum(), "bear", (bear&ev).sum())
obs = np.where(bull, hitL, hitH)[ev]
print("observed rate", obs.mean())
# Null 1: same as original: random 15m close within +-30d, same ATR distance, same side
rng = np.random.default_rng(1)
evi = np.flatnonzero(ev); ctn = ct.asi8; W = 30*86400*10**9
okgrid = np.flatnonzero(fin & valid)
lo = np.searchsorted(ctn[okgrid], ctn[evi]-W); hi = np.searchsorted(ctn[okgrid], ctn[evi]+W, "right")
sd_bull = bull[evi]; dist = np.where(sd_bull, -dL[evi], dH[evi]) # signed ATR distance of level from price (neg=below)
def null_rate(pick):
    res=[]
    for r in range(5):
        j = okgrid[pick(r)]
        lev = px0[j] + dist*atr[j]
        hh = np.where(sd_bull, hit_below(i0[j], lev), hit_above(i0[j], lev))
        res.append(hh)
    return np.mean(res, 0)
nr1 = null_rate(lambda r: lo + (rng.random(len(evi))*(hi-lo)).astype(int))
print("null1 (orig design, my code): %.4f diff %.4f" % (nr1.mean(), obs.mean()-nr1.mean()))
# Null 2: ToD-matched: same NY 15m slot, other days within +-30d
ny = ct.tz_convert("America/New_York"); slot = (ny.hour*60+ny.minute).to_numpy()
pairs = {}
nr2 = np.full(len(evi), np.nan); acc=[]
df = pd.DataFrame({"t":ctn[okgrid], "slot":slot[okgrid], "g":okgrid})
groups = {s: g for s, g in df.groupby("slot")}
res=[]
for r in range(5):
    out = np.full(len(evi), np.nan)
    for s, gi in pd.Series(np.arange(len(evi))).groupby(slot[evi]):
        g = groups[s]; T = g.t.to_numpy(); G = g.g.to_numpy()
        e = gi.to_numpy(); te = ctn[evi[e]]
        a = np.searchsorted(T, te-W); z = np.searchsorted(T, te+W, "right")
        j = G[a + (rng.random(len(e))*(z-a)).astype(int)]
        lev = px0[j] + dist[e]*atr[j]
        out[e] = np.where(sd_bull[e], hit_below(i0[j], lev), hit_above(i0[j], lev))
    res.append(out)
nr2 = np.mean(res,0)
print("null2 (ToD-matched): %.4f diff %.4f" % (nr2.mean(), obs.mean()-nr2.mean()))
# Null 3: non-FVG bars' own extreme. Stratify by side, |distance| decile, NY hour, and bar direction.
allv = fin & valid
rows = pd.DataFrame({
  "fvg": np.r_[ev[allv & ~bear], ev[allv & ~bull]],  # low-side uses bull FVGs, high side bear
  "side": np.r_[np.zeros((allv&~bear).sum()), np.ones((allv&~bull).sum())],
  "d": np.r_[dL[allv&~bear], dH[allv&~bull]],
  "hit": np.r_[hitL[allv&~bear], hitH[allv&~bull]],
  "hr": np.r_[ny.hour[allv&~bear], ny.hour[allv&~bull]],
  "yr": np.r_[ct.year[allv&~bear], ct.year[allv&~bull]]})
rows["db"] = pd.cut(rows.d, [-np.inf,0,0.05,0.1,0.15,0.2,0.3,0.4,0.5,0.6,0.8,1.0,1.3,1.7,2.5,np.inf])
cell = rows.groupby(["side","db","hr"], observed=True)
base = rows[~rows.fvg].groupby(["side","db","hr"], observed=True).hit.mean().rename("base")
f = rows[rows.fvg].join(base, on=["side","db","hr"])
print("null3 (non-FVG bars, own extreme, strat side x dist x NYhour): fvg %.4f base %.4f diff %.4f n %d" % (
      f.hit.mean(), f.base.mean(), (f.hit-f.base).mean(), f.base.notna().sum()))
for half,(a,z) in {"H1":(2016,2020),"H2":(2021,2026)}.items():
    s=f[(f.yr>=a)&(f.yr<=z)]; print("  ", half, "diff %.4f" % (s.hit-s.base).mean())
# daily-block bootstrap CI for null3 and null2 diffs
day = pd.DatetimeIndex(ct[evi]).tz_convert("America/New_York").floor("D")
def boot(x):
    s = pd.Series(x).groupby(day.values).agg(["sum","count"]); S=s["sum"].to_numpy(); C=s["count"].to_numpy()
    r = np.random.default_rng(7); k=r.integers(0,len(S),(2000,len(S)))
    v = S[k].sum(1)/C[k].sum(1); return np.percentile(v,[2.5,97.5])
print("null2 diff CI", boot(obs-nr2))
# null3 per-event vector aligned to evi order
f3 = rows[rows.fvg].copy()
print("distance summary of events (ATR):", pd.Series(np.abs(dist)).describe().round(3).to_dict())
# day-block CI on null3
f3 = rows[rows.fvg & rows.index.isin(f.index)]
evday = np.r_[ct[allv&~bear], ct[allv&~bull]]
dd = pd.DatetimeIndex(evday[f.index]).tz_convert("America/New_York").floor("D")
x = (f.hit - f.base).to_numpy(float); m = np.isfinite(x)
s = pd.Series(x[m]).groupby(dd[m].values).agg(["sum","count"]); S=s["sum"].to_numpy(); C=s["count"].to_numpy()
k=np.random.default_rng(7).integers(0,len(S),(2000,len(S)))
print("null3 diff CI", np.percentile(S[k].sum(1)/C[k].sum(1),[2.5,97.5]))
# same with finer distance bins (0.02 ATR) + hour
rows["db2"] = np.floor(rows.d.clip(-1,3)/0.02)
base2 = rows[~rows.fvg].groupby(["side","db2","hr"]).hit.mean().rename("base")
g = rows[rows.fvg].join(base2, on=["side","db2","hr"])
print("null3b fine bins diff %.4f" % (g.hit-g.base).mean())
