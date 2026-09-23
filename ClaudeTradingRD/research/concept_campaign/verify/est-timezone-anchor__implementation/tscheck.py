import sys, numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
m1 = cl.load_m1()
ny = m1.index.tz_convert("America/New_York")
rg = (m1.high - m1.low).to_numpy()
df = pd.DataFrame({"r": rg, "hm": ny.hour*100+ny.minute, "wd": ny.dayofweek, "d": ny.date, "dom": ny.day}, index=m1.index)
# median-normalised range by minute of day, 07:50-09:45 weekdays
df["rn"] = df.r / df.groupby("d").r.transform("median")
w = df[(df.wd < 5)]
t = w.groupby("hm").rn.mean()
print(t.loc[[755,758,759,800,801,802,805,815,825,828,829,830,831,832,835,845,855,859,900,901,925,929,930,931,935,959,1000,1001]].round(2).to_string())
# NFP: first Friday; argmax minute between 07:00 and 10:00
f = w[(w.wd == 4) & (w.dom <= 7) & (w.hm >= 700) & (w.hm < 1000)]
am = f.groupby("d").apply(lambda g: g.hm.iloc[np.argmax(g.r.to_numpy())])
print("NFP-Friday argmax minute counts:", am.value_counts().head(8).to_dict())
