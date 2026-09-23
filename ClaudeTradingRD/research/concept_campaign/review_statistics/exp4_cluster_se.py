"""Reported SE vs a day-cluster bootstrap SE on the same daily-bias-shaped noise book."""
from common import *
t_utc = pd.DatetimeIndex(pd.to_datetime(TN).tz_localize("UTC"))
td = np.asarray(cl.trading_day(t_utc))
grid = np.flatnonzero((NY.minute.to_numpy() % 15) == 0)
days_u, day_idx = np.unique(td[grid], return_inverse=True)
for s in range(3):
    rng = np.random.default_rng(9000 + s)
    pick = rng.random(len(days_u)) < 0.6
    ddir = rng.choice([-1, 1], len(days_u))
    sel = pick[day_idx]
    ev = events_from_pos(grid[sel], ddir[day_idx][sel], 4.0, 2.0)
    r = cl.trade_test(ev, max_hold="4h", n_boot=1000, blocks=False, keep_trades=True)
    tr = r["_trades"]
    d = (tr.net_R - tr.ctrl_mean_R).to_numpy()
    day = np.asarray(cl.trading_day(pd.DatetimeIndex(tr.decision_time)))
    u, inv = np.unique(day, return_inverse=True)
    sums = np.bincount(inv, weights=d); cnts = np.bincount(inv)
    b = np.random.default_rng(1)
    bs = []
    for _ in range(1000):
        k = b.integers(0, len(u), len(u))
        bs.append(sums[k].sum() / cnts[k].sum())
    rep_se = (r["ci_hi"] - r["ci_lo"]) / 3.92
    print(f"seed {s}: n={r['n']} days={len(u)} diff={r['diff']:+.4f} reported SE={rep_se:.4f} ({r['ci_method']}) day-cluster SE={np.std(bs):.4f} ratio={np.std(bs)/rep_se:.2f}")
