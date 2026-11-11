"""TRAIN grid for hedge_avg.py, then the best cell once on TEST and the last two weeks."""
import numpy as np, pandas as pd
from hedge_avg import P, run
from range_scalp import prep
from data import load_m1
d = prep(load_m1()); dates = np.unique(d.index.date); cut = pd.Timestamp(dates[int(len(dates) * .6)], tz="UTC")
sets = {"TRAIN": d[d.index < cut], "TEST": d[d.index >= cut], "LAST2W": d[d.index >= d.index[-1] - pd.Timedelta(days=14)]}
def row(part, **kw):
    t, dd = run(part, P(**kw)); a = dd[dd.index.isin(t.day)]; w, lo = t.pnl[t.pnl > 0], t.pnl[t.pnl <= 0]
    m = t.why.value_counts(normalize=True).mul(100).round(0)
    return dict(tr_day=round(len(t) / len(a), 1), win=round(len(w) / len(t) * 100, 1), pf=round(w.sum() / -lo.sum(), 2), clips=round(t.clips.mean(), 2), hold=float(t.mins.median()),
                worst=round(a.pct.min(), 2), best=round(a.pct.max(), 2), red=round((a.pct < 0).mean() * 100), total=round((dd.end.iloc[-1] / dd.start.iloc[0] - 1) * 100, 1),
                pct_be=m.get("breakeven", 0), pct_stop=m.get("stop", 0), pct_time=m.get("time", 0) + m.get("flat", 0), pct_nomove=m.get("no move", 0))
cells = [dict(be=be, tpa=tpa, step=st, K=K, max_hold=hm) for be in ("side", "cycle") for tpa in (1.0, 2.0) for st in (1.5, 2.5) for K in (2, 4) for hm in (10, 60, 240)]
r = pd.DataFrame([{**kw, **row(sets["TRAIN"], **kw)} for kw in cells]).sort_values("pf", ascending=False); r.to_csv("hedge_grid_train.csv", index=False)
print("TRAIN grid, best 12 (pct_* = share of cycles ending at breakeven / hard stop / time or flat / neither side reached its target)")
print(r.head(12).to_string(index=False)); print("\nbest 3 with the whole-cycle breakeven exit"); print(r[r.be == "cycle"].head(3).to_string(index=False))
kw = {k: (r.iloc[0][k].item() if hasattr(r.iloc[0][k], "item") else r.iloc[0][k]) for k in ("be", "tpa", "step", "K", "max_hold")}
print("\nBest on TRAIN, once on TEST / last two weeks:", kw)
for n, part in sets.items(): print(f"  {n:<7}", row(part, **kw))
print("zero cost:")
for n, part in sets.items(): print(f"  {n:<7}", row(part, cost=0.0, **kw))
