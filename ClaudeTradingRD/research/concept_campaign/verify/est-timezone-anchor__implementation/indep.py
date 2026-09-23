"""Independent reimplementation: per NY clock :00/:30 mark, P(sum M1 range next 15 > prev 15)."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
m1 = cl.load_m1()
print(m1.index[:3], m1.columns.tolist(), len(m1))
idx = m1.index.tz_convert("UTC")
r = (m1["high"] - m1["low"]).to_numpy()
s = pd.Series(r, index=idx)
# rolling sums over exactly 15 consecutive minutes; require full coverage
full = pd.Series(1.0, index=idx)
# reindex to a complete minute grid
grid = pd.date_range(idx.min(), idx.max(), freq="1min", tz="UTC")
sr = s.reindex(grid); cnt = full.reindex(grid).fillna(0)
before = sr.rolling(15).sum().shift(1)          # [T-15, T)
bcnt = cnt.rolling(15).sum().shift(1)
after = sr[::-1].rolling(15).sum()[::-1]         # [T, T+15)
acnt = cnt[::-1].rolling(15).sum()[::-1]
ok = (bcnt == 15) & (acnt == 15) & sr.notna()
out = pd.DataFrame({"y": (after > before).astype(float), "ok": ok})
out = out[out.ok & (grid.minute % 30 == 0)]
ny = out.index.tz_convert("America/New_York")
out["nyhm"] = ny.hour * 100 + ny.minute
out["wd"] = ny.dayofweek
out["dst"] = np.array([bool(t.dst()) for t in ny])
out = out[out.wd < 5]
out["year"] = out.index.tz_convert("America/New_York").year
tab = out.groupby("nyhm").y.agg(["mean", "size"])
print(tab.to_string())
print("overall :30 marks mean", out[out.index.minute == 30].y.mean() if False else out[(out.nyhm % 100) == 30].y.mean())
for d in (True, False):
    o = out[out.dst == d]
    print("DST" if d else "STD", o.groupby("nyhm").y.mean().loc[[630,700,730,800,830,900,930,1000,1030]].round(3).to_dict())
o = out[out.nyhm == 830]
print("08:30 by year", o.groupby("year").y.mean().round(3).to_dict())
out.to_pickle("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/est-timezone-anchor__implementation/marks.pkl")
