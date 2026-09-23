"""Scratch: decompose est-timezone-anchor reading b into winter/summer days; no write_result."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
from concept_lab.data import utc_ns

m1 = cl.load_m1(); mkt = cl.get_market(m1); tn = mkt.tn
cs = np.concatenate([[0.0], np.cumsum(mkt.h - mkt.l)]); k = 15; one = np.int64(60_000_000_000)
def score(times):
    tt = pd.DatetimeIndex(times); out = np.full(len(tt), np.nan); ok0 = ~tt.isna()
    q = utc_ns(tt[ok0]); p = np.searchsorted(tn, q, side="left")
    good = (p - k >= 0) & (p + k - 1 < len(tn)); pc = np.clip(p, k, len(tn) - k)
    good &= (tn[np.minimum(p, len(tn) - 1)] == q)
    good &= (tn[pc + k - 1] == q + (k - 1) * one) & (tn[pc - k] == q - k * one)
    v = np.where(good, ((cs[pc + k] - cs[pc]) > (cs[pc] - cs[pc - k])).astype(float), np.nan)
    out[np.flatnonzero(ok0)] = v; return out

start = m1.index.min().tz_convert("UTC").normalize(); end = m1.index.max().tz_convert("UTC").normalize()
dates = pd.date_range(start.tz_localize(None), end.tz_localize(None), freq="D"); dates = dates[dates.dayofweek < 5]
Ta = pd.DatetimeIndex(dates + pd.Timedelta(hours=8, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
Tb = pd.DatetimeIndex(dates + pd.Timedelta(hours=8, minutes=30)).tz_localize("Etc/GMT+5").tz_convert("UTC")
summer = np.asarray(Ta != Tb)
oa, ob = score(Ta), score(Tb)
def rate(x, m): x = x[m]; x = x[np.isfinite(x)]; return round(x.mean(), 4), len(x)
print("reading a all", rate(oa, np.ones(len(oa), bool)), " b all", rate(ob, np.ones(len(ob), bool)))
print("WINTER (a==b)", rate(ob, ~summer))
print("SUMMER a (08:30 EDT=12:30Z)", rate(oa, summer), " b (09:30 NY=13:30Z)", rate(ob, summer))
# NY-clock levels in summer for comparison: every half hour 07:00..11:00 NY
for hh in ["07:00","07:30","08:00","08:30","09:00","09:30","10:00","10:30","11:00","12:30","13:30","14:00"]:
    h, m = map(int, hh.split(":"))
    T = pd.DatetimeIndex(dates + pd.Timedelta(hours=h, minutes=m)).tz_localize("America/New_York").tz_convert("UTC")
    o = score(T)
    print("NY", hh, "all", rate(o, np.ones(len(o), bool)), "summer", rate(o, summer), "winter", rate(o, ~summer))
# fixed 13:30 UTC ... the same thing as b; also fixed-UTC-5 07:30 / 09:30 for contrast
for hh in ["07:30","09:30"]:
    h, m = map(int, hh.split(":"))
    T = pd.DatetimeIndex(dates + pd.Timedelta(hours=h, minutes=m)).tz_localize("Etc/GMT+5").tz_convert("UTC")
    o = score(T); print("fixedEST", hh, rate(o, np.ones(len(o), bool)), "summer", rate(o, summer))
# Year-by-year for b
yrs = Tb.year
for y in sorted(set(yrs)):
    mm = np.asarray(yrs == y); print(y, "b", rate(ob, mm), "a", rate(oa, mm))
# Null (no rate_test call, so nothing is ledgered): same sample_times draw as the script
keep = np.isfinite(ob); T = Tb[keep].as_unit("ns"); o = ob[keep]
rt = cl.sample_times(T, 5, 30, seed=cl.rules.SEED)
nulls = np.column_stack([score(pd.DatetimeIndex(rt[:, j]).tz_localize("UTC")) for j in range(5)])
nr = np.nanmean(nulls); print("b obs", o.mean(), "null", nr, "diff", o.mean() - nr)
sm = summer[keep]
print("b winter diff", o[~sm].mean() - np.nanmean(nulls[~sm]), " b summer diff", o[sm].mean() - np.nanmean(nulls[sm]))
