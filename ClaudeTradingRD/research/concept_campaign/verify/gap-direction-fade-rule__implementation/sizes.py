import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
a = pd.read_csv("events_a.csv", parse_dates=["t"])
mkt = cl.get_market()
a["absd"] = (a.pc - a.px).abs()
a["rel"] = a.absd / a.prange
a["yr"] = a.t.dt.year
print(a.absd.describe())
a["q"] = pd.qcut(a.rel, 4, labels=False)
g = a.groupby("q").agg(n=("obs","size"), rel=("rel","median"), usd=("absd","median"), toward=("obs","mean"), away=("away","mean"))
g["diff"] = g.toward - g.away; print(g)
for u in (True, False):
    s = a[a.up == u]; print("up" if u else "dn", s.groupby("q").apply(lambda x: round(x.obs.mean()-x.away.mean(),3)).to_dict())
# unconditional drift: all reopens, bid change from 18:01 open to +60 bars close, and first-bar range vs later
i0 = a.i0.to_numpy()
drift = mkt.c[np.minimum(i0+59, len(mkt.c)-1)] - mkt.o[i0]
print("mean drift 60 bars (all)", drift.mean(), "median", np.median(drift))
print("drift in gap-direction-signed (+ = toward fill)", np.mean(np.where(a.up, -drift, drift)))
# M1 range by minute after reopen
for off in (0,1,2,5,10,20,30,59):
    r = mkt.h[i0-1+off]-mkt.l[i0-1+off]; print("offset", off, "median M1 range", round(np.median(r),3))
# first-minute return (bar s, the reopen bar) close - open and 18:01->18:05 direction for all reopens
r1 = mkt.c[i0+4]-mkt.o[i0]
print("18:01->18:05 mean move", r1.mean(), "gap-up", r1[a.up].mean(), "gap-dn", r1[~a.up].mean())
