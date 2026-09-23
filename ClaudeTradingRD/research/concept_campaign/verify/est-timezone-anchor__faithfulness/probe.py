import sys, numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
from concept_lab.data import utc_ns
m1 = cl.load_m1(); mkt = cl.get_market(m1); tn = mkt.tn
cs = np.concatenate([[0.0], np.cumsum(mkt.h - mkt.l)]); k = 15; one = np.int64(60_000_000_000)
def score(tt):
    q = utc_ns(tt); p = np.searchsorted(tn, q)
    pc = np.clip(p, k, len(tn)-k)
    good = (tn[np.minimum(p,len(tn)-1)] == q) & (tn[pc+k-1] == q+(k-1)*one) & (tn[pc-k] == q-k*one)
    a = cs[pc+k]-cs[pc]; b = cs[pc]-cs[pc-k]
    return np.where(good, (a>b).astype(float), np.nan)
start = m1.index.min().tz_convert("UTC").normalize().tz_localize(None)
end = m1.index.max().tz_convert("UTC").normalize().tz_localize(None)
dates = pd.date_range(start, end, freq="D"); dates = dates[dates.dayofweek<5]
def rate(h, mnt, tz="America/New_York", mask=None):
    T = pd.DatetimeIndex(dates + pd.Timedelta(hours=h, minutes=mnt)).tz_localize(tz, nonexistent="NaT", ambiguous="NaT").tz_convert("UTC")
    s = score(T)
    if mask is not None: s = np.where(mask, s, np.nan)
    return np.nanmean(s), np.isfinite(s).sum(), s
# DST flag per date
loc = pd.DatetimeIndex(dates + pd.Timedelta(hours=12)).tz_localize("America/New_York")
dst = np.array([t.dst() != pd.Timedelta(0) for t in loc])
print("DST share", dst.mean())
print("--- every half hour on NY clock, 03:00-14:00 (all / winter / summer)")
for h in range(3, 15):
    for mnt in (0, 30):
        r, n, _ = rate(h, mnt); rw, nw, _ = rate(h, mnt, mask=~dst); rs, ns, _ = rate(h, mnt, mask=dst)
        print(f"{h:02d}:{mnt:02d} NY  all {r:.3f} (n={n})  winter {rw:.3f}  summer {rs:.3f}")
print("--- fixed-offset / other clock 08:30 placebos")
for tz in ["Etc/GMT+5", "Etc/GMT+6", "America/Chicago", "UTC", "Europe/London"]:
    r, n, _ = rate(8, 30, tz); print(tz, f"{r:.3f} n={n}")
# summer-only discriminator: 12:30 UTC (NY 08:30 EDT) vs 13:30 UTC (b)
r,n,sa = rate(8,30,mask=dst); r2,n2,sb = rate(8,30,"Etc/GMT+5",mask=dst)
print("summer only: a(08:30 EDT)=%.3f  b(09:30 EDT)=%.3f"%(r,r2))
# a: by year & by weekday & excluding first Friday
r,n,s = rate(8,30)
df = pd.DataFrame({"d":dates,"s":s}).dropna()
print(df.groupby(df.d.dt.year).s.agg(['mean','size']).T.round(3))
print(df.groupby(df.d.dt.dayofweek).s.agg(['mean','size']).T.round(3))
ff = (df.d.dt.dayofweek==4)&(df.d.dt.day<=7)
print("excl first Fridays", df.s[~ff].mean(), "first Fri", df.s[ff].mean())
