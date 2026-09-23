import sys, numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
m1 = cl.load_m1()
ev = pd.read_parquet("ev_orig.parquet")
hb = cl.build_bars(m1, "1h"); print("1h index minutes:", pd.Series(hb.index.minute).value_counts().head(3).to_dict())
# independent: per event, scan raw M1 slices
H, L = m1["high"], m1["low"]
hr = m1.index.floor("h")
# prior-hour extremes via groupby on M1 floor hour
g = m1.groupby(hr).agg(hh=("high","max"), ll=("low","min"))
dec = pd.DatetimeIndex(ev.decision_time)
hs = dec.floor("h")
el = (dec - hs) / pd.Timedelta("1min")
# running hi/lo within [hs, dec): use cumulative within hour on M1
cm = pd.DataFrame({"h": H.groupby(hr).cummax(), "l": L.groupby(hr).cummin(), "hr": hr}, index=m1.index)
# M1 bar whose CLOSE <= dec, i.e. start <= dec-1min
pos = m1.index.searchsorted(dec - pd.Timedelta("1min"), "right") - 1
rh = np.where(pos >= 0, cm["h"].to_numpy()[pos], np.nan); rl = np.where(pos >= 0, cm["l"].to_numpy()[pos], np.nan)
same = (pos >= 0) & (cm["hr"].to_numpy()[pos] == hs)
rh[~same] = np.nan; rl[~same] = np.nan
gi = g.index.searchsorted(hs, "left") - 1        # last hour group strictly before hs
ph = np.where(gi >= 0, g.hh.to_numpy()[gi], np.nan); pl = np.where(gi >= 0, g.ll.to_numpy()[gi], np.nan)
d = ev.direction.to_numpy()
exp_ = np.where(d == 1, rh > ph, rl < pl) & ~np.isnan(rh) & ~np.isnan(ph)
for lm in (20,):
    mine = exp_ & (el >= lm)
    print("agree", (mine == ev.late_expanded.to_numpy()).mean(), mine.mean(), "disagree n", (mine != ev.late_expanded.to_numpy()).sum())
ev2 = ev.copy()
ev2["exp_any"] = exp_; ev2["late"] = np.asarray(el >= 20)
for lm in (10, 30, 40):
    ev2[f"late{lm}"] = exp_ & np.asarray(el >= lm)
ev2["early_exp"] = exp_ & np.asarray(el < 20)
ev2["mine20"] = exp_ & np.asarray(el >= 20)
ev2.to_parquet("ev_mine.parquet")
