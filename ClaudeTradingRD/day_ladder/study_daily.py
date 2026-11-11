"""Daily-movement study of gold: when it moves, and whether short moves continue or reverse, by UTC hour.
TRAIN = first 60% of days (used to choose rules); TEST = rest (reported only)."""
import numpy as np, pandas as pd
from data import load_m1, atr

d = load_m1(); d["atr"] = atr(d, 30); d["hour"] = d.index.hour; d["day"] = d.index.date
days = sorted(d.day.unique()); cut = days[int(len(days) * 0.6)]
print(f"bars {len(d):,}  {d.index[0]} -> {d.index[-1]}  days {len(days)}  TRAIN < {cut}")

# 1. Daily range and where in the day the extremes form
g = d.groupby("day")
dr = (g.high.max() - g.low.min()); dr = dr[g.size() > 600]
print("\nDaily range (pts) quantiles:", dr.quantile([.1, .25, .5, .75, .9]).round(1).to_dict())
print("Daily |close-open| / range median:", ((g.close.last() - g.open.first()).abs() / (g.high.max() - g.low.min())).median().round(2))
hi_h = g.apply(lambda x: x.high.idxmax().hour); lo_h = g.apply(lambda x: x.low.idxmin().hour)
ext = (hi_h.value_counts() + lo_h.value_counts()).fillna(0) / (2 * len(hi_h)) * 100

# 2. Per-hour: size of movement, and what a 5-minute push does next
d["r5"] = d.close - d.close.shift(5)                       # last 5 closed minutes
for h in (5, 15, 30):
    d[f"f{h}"] = d.close.shift(-h) - d.close             # forward move from this close
d["push"] = d.r5 / d.atr                                    # push size in M1-ATR(30) units
rows = []
for name, part in (("TRAIN", d[d.day < cut]), ("TEST", d[d.day >= cut])):
    for h, x in part.groupby("hour"):
        hr = x.groupby("day").apply(lambda z: z.high.max() - z.low.min())
        big = x[x.push.abs() >= 2.0].iloc[::5]              # a 5-min move of >= 2 ATR, thinned to cut overlap
        s = np.sign(big.r5)
        rows.append(dict(set=name, hour=h, hr_range=hr.median(), atr=x.atr.median(), n_push=len(big),
                         cont5=(s * big.f5).mean(), cont15=(s * big.f15).mean(), cont30=(s * big.f30).mean(),
                         t15=(s * big.f15).mean() / ((s * big.f15).std() / np.sqrt(max(len(big), 1)))))
t = pd.DataFrame(rows)
w = t.pivot(index="hour", columns="set", values=["hr_range", "n_push", "cont15", "t15"]).round(2)
w["ext%"] = ext.reindex(w.index).round(1)
print("\nBy UTC hour — hr_range: median hourly range (pts); cont15: avg pts gold CONTINUES in the push direction over the next 15 min after a >=2-ATR 5-min push (negative = it reverses); t15: t-stat; ext%: share of daily highs/lows formed")
print(w.to_string())
t.to_csv("study_by_hour.csv", index=False)

# 3. Does the trend so far today carry on? (direction since 00:00 UTC vs next hour)
d["day_open"] = g.open.transform("first"); d["sofar"] = d.close - d.day_open
hh = d[d.index.minute == 0].copy(); hh["next60"] = d.close.shift(-60).reindex(hh.index) - hh.close
for name, part in (("TRAIN", hh[hh.day < cut]), ("TEST", hh[hh.day >= cut])):
    p = part[(part.sofar.abs() > part.atr * 5)]
    print(f"{name}: next-hour move in the direction of the day so far: mean {(np.sign(p.sofar) * p.next60).mean():+.2f} pts, same-direction {((np.sign(p.sofar) * p.next60) > 0).mean():.1%}, n={len(p)}")
