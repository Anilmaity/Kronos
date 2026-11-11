"""Bold ladder: every basket risks the whole room down to the day's floor. TRAIN grid, then the pick on TEST / last 2 weeks."""
import sys
import numpy as np, pandas as pd
from ladder import P, prep, run
from data import load_m1

d = prep(load_m1()); dates = np.unique(d.index.date); cut = pd.Timestamp(dates[int(len(dates) * .6)], tz="UTC")
sets = {"TRAIN": d[d.index < cut], "TEST": d[d.index >= cut], "LAST2W": d[d.index >= d.index[-1] - pd.Timedelta(days=14)]}

def stats(part, **kw):
    p = P(mode="press", base_pct=100, max_pct=100, trail=99, max_hold=180, **kw)
    t, dd, _ = run(part, p); a = dd[dd.index.isin(t.day)]; w, lo = t.pnl[t.pnl > 0], t.pnl[t.pnl <= 0]
    return dict(days=len(a), tr_day=round(len(t) / len(a), 1), win=round(len(w) / len(t) * 100, 1), pf=round(w.sum() / -lo.sum(), 2),
                worst=round(a.pct.min(), 2), best=round(a.pct.max(), 1), d6=round((a.pct >= 6).mean() * 100, 1),
                d20=round((a.pct >= 20).mean() * 100, 1), red=round((a.pct < 0).mean() * 100), mean=round(a.pct.mean(), 2),
                hold=t.mins.median(), total=round((dd.end.iloc[-1] / dd.start.iloc[0] - 1) * 100, 1)), dd, t

if "pick" not in sys.argv:
    rows = [dict(s_atr=S, pull=pull, giveback=g, **stats(sets["TRAIN"], s_atr=S, s_min=S, pull=pull, giveback=g)[0])
            for S in (6.0, 9.0, 12.0) for pull in (1.0, 1.5) for g in (3.0, 6.0)]
    r = pd.DataFrame(rows).sort_values("d6", ascending=False); r.to_csv("grid_bold_train.csv", index=False); print(r.to_string(index=False))
else:
    S, pull, g = map(float, sys.argv[2:5])
    for cost in (0.6, 0.9, 0.0):
        for n, part in sets.items():
            s, dd, t = stats(part, s_atr=S, s_min=S, pull=pull, giveback=g, cost=cost); print(f"cost {cost} {n:<7}", s)
            if cost == 0.6 and n == "LAST2W":
                print(dd.assign(trades=t.groupby("day").size(), wins=t[t.pnl > 0].groupby("day").size()).fillna(0).round(2).to_string())
