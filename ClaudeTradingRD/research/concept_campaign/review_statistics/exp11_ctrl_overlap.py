"""How often does a control entry land on a moment where the concept itself fired
(same minute), and with the same direction the concept had there?"""
from common import *
from concept_lab.engine import sample_times
t_utc = pd.DatetimeIndex(pd.to_datetime(TN).tz_localize("UTC"))
td = np.asarray(cl.trading_day(t_utc))
grid = np.flatnonzero((NY.minute.to_numpy() % 15) == 0)
days_u, day_idx = np.unique(td[grid], return_inverse=True)
# a persistent-regime concept: direction = sign of the prior 20-day return (known), fires on every M15 mark
c = M1["close"].to_numpy()
day_close = pd.Series(c[grid]).groupby(day_idx).last().to_numpy()
mom = np.sign(pd.Series(day_close).diff(20).shift(1).to_numpy())
ok = np.isfinite(mom[day_idx])
pos = grid[ok]; dirs = mom[day_idx][ok].astype(int)
d = t_utc[pos]
ct = sample_times(d, 5, 30, 20260825)
ctn = ct.ravel()
real_ns = TN[pos]
hit = np.isin(ctn, real_ns)
src_dir = np.repeat(dirs, 5)
where = np.searchsorted(real_ns, ctn); where = np.clip(where, 0, len(real_ns) - 1)
same_dir = hit & (dirs[where] == src_dir)
print(f"events {len(pos):,}; control draws landing on a real event minute: {hit.mean():.1%}; "
      f"...and with the concept's own direction there: {same_dir.mean():.1%}")
