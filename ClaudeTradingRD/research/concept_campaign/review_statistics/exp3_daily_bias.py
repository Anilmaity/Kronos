"""'Daily bias' shaped noise: pick a random direction per NY trading day, then take
every 15-minute mark of that day in that direction (the typical 'trade with the daily
bias' book). The direction carries no information."""
import sys
from common import *
NS = int(sys.argv[1]) if len(sys.argv) > 1 else 60
t_utc = pd.DatetimeIndex(pd.to_datetime(TN).tz_localize("UTC"))
td = np.asarray(cl.trading_day(t_utc))
grid = np.flatnonzero((NY.minute.to_numpy() % 15) == 0)
days_u, day_idx = np.unique(td[grid], return_inverse=True)
out = []
for s in range(NS):
    rng = np.random.default_rng(9000 + s)
    pick = rng.random(len(days_u)) < 0.6          # ~60% of days have a 'bias'
    ddir = rng.choice([-1, 1], len(days_u))
    sel = pick[day_idx]
    pos = grid[sel]
    dirs = ddir[day_idx][sel]
    ev = events_from_pos(pos, dirs, 4.0, 2.0)
    r = cl.trade_test(ev, max_hold="4h", n_boot=1000, blocks=False)
    h = r["halves"]
    out.append((s, r["n"], r["diff"], r["ci_lo"], r["ci_hi"], r["ci_method"], r["mde"], r["verdict"], z(r), h["H1"]["diff"], h["H2"]["diff"]))
    print(out[-1], flush=True)
df = pd.DataFrame(out, columns="seed n diff lo hi how mde verdict z h1 h2".split())
print(df.verdict.value_counts())
se = (df.hi - df.lo) / 3.92
print("z sd", df.z.std(), "frac |z|>1.96", (df.z.abs() > 1.96).mean(), "emp sd/rep se", df['diff'].std() / se.mean())
df.to_csv("exp3_daily_bias.csv", index=False)
