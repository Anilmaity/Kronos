"""TRAIN-only grid: how often can the ladder reach +6 % / +20 % days inside the -2.5 % floor?"""
import numpy as np, pandas as pd
from ladder import P, prep, run
from data import load_m1

d = prep(load_m1()); dates = np.unique(d.index.date); cut = pd.Timestamp(dates[int(len(dates) * .6)], tz="UTC")
train = d[d.index < cut]
rows = []
for base in (1.25, 2.5):
    for press in (1.0, 2.0, 3.0):
        for mx in (3.0, 6.0, 10.0):
            for trail in (4.0, 99.0):
                for pull in (0.5, 1.0):
                    p = P(mode="press", base_pct=base, press=press, max_pct=mx, trail=trail, pull=pull, max_hold=180, giveback=3.0)
                    t, dd, _ = run(train, p); a = dd[dd.index.isin(t.day)]
                    w, lo = t.pnl[t.pnl > 0], t.pnl[t.pnl <= 0]
                    rows.append(dict(base=base, press=press, max=mx, trail=trail, pull=pull, tr_day=round(len(t) / len(a), 1),
                                     win=round(len(w) / len(t) * 100, 1), pf=round(w.sum() / -lo.sum(), 2), worst=round(a.pct.min(), 2),
                                     best=round(a.pct.max(), 1), d6=round((a.pct >= 6).mean() * 100, 1), d20=round((a.pct >= 20).mean() * 100, 1),
                                     red=round((a.pct < 0).mean() * 100), mean=round(a.pct.mean(), 2)))
r = pd.DataFrame(rows).sort_values("d6", ascending=False); r.to_csv("grid_press_train.csv", index=False)
print(r.head(14).to_string(index=False))
