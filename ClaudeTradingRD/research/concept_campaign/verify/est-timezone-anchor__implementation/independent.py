import numpy as np, pandas as pd
d = pd.read_parquet('/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xau_m1_full.parquet')
d['time'] = pd.to_datetime(d['time'], utc=True)
d = d[d.time >= '2016-01-01 13:19'].drop_duplicates('time').sort_values('time').reset_index(drop=True)
t = d.time.values.astype('datetime64[m]').astype(np.int64)  # minutes
rng_ = (d.high - d.low).to_numpy()
idx = pd.Series(np.arange(len(t)), index=t)
cs = np.concatenate([[0], np.cumsum(rng_)])
K = 15
def score(Tm):
    out = np.full(len(Tm), np.nan)
    for i, q in enumerate(Tm):
        p = idx.get(q)
        if p is None or p - K < 0 or p + K > len(t): continue
        if t[p + K - 1] != q + K - 1 or t[p - K] != q - K: continue
        out[i] = float(cs[p + K] - cs[p] > cs[p] - cs[p - K])
    return out
days = pd.date_range('2016-01-01', '2026-07-23', freq='D'); days = days[days.dayofweek < 5]
rs = np.random.default_rng(1)
cand = t[(t % 30) == 0]
for name, tz in [('a', 'America/New_York'), ('b', 'Etc/GMT+5')]:
    T = (days + pd.Timedelta('8h30min')).tz_localize(tz).tz_convert('UTC')
    Tm = T.values.astype('datetime64[m]').astype(np.int64)
    obs = score(Tm); k = np.isfinite(obs); Tm, obs, Tk = Tm[k], obs[k], T[k]
    nulls = []
    for q in Tm:
        lo, hi = np.searchsorted(cand, q - 30*1440), np.searchsorted(cand, q + 30*1440, 'right')
        nulls.append(rs.choice(cand[lo:hi], 5))
    ns = score(np.concatenate(nulls)).reshape(-1, 5)
    nr = np.nanmean(ns)
    ny = Tk.tz_convert('America/New_York')
    dst = np.array([x.dst() != pd.Timedelta(0) for x in ny])
    print(name, 'n', len(obs), 'obs %.3f null %.3f diff %+.3f' % (obs.mean(), nr, obs.mean() - nr))
    print('   DST-days obs %.3f (n=%d) | winter obs %.3f (n=%d)' % (obs[dst].mean(), dst.sum(), obs[~dst].mean(), (~dst).sum()))
    # tod-matched null: same UTC clock on other days (tests clock-specific step vs a random day's same moment)
    yrs = pd.DatetimeIndex(Tk).year
    for y in (2016, 2019, 2022, 2025): print('   ', y, '%.3f' % obs[yrs == y].mean())
