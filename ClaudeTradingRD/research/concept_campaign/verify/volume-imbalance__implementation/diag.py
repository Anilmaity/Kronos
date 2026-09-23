import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
t = pd.read_pickle("trades_orig.pkl")
m1 = cl.load_m1(); mi = pd.DatetimeIndex(m1.index).tz_convert("UTC")
t["yr"] = t.decision_time.dt.year
t["d"] = t.net_R - t.ctrl_mean_R
print(t.groupby("yr").agg(n=("d","size"), diff=("d","mean"), risk_med=("risk","median"), R=("net_R","mean"), ctrl=("ctrl_mean_R","mean")).round(3))
# entry jump: entry open vs previous M1 close, signed by direction (positive = adverse for the trade)
pos = mi.get_indexer(pd.DatetimeIndex(t.entry_time))
prevc = m1.close.to_numpy()[pos-1]
t["jump"] = (t.entry.to_numpy() - prevc) * t.direction
t["jump_R"] = t.jump / t.risk
print(t.groupby("yr")[["jump","jump_R"]].median().round(3))
print("mean jump_R by yr", t.groupby("yr").jump_R.mean().round(3).to_dict())
# unconditional M1 open-prevclose |jump| by year
o = m1.open.to_numpy(); c = m1.close.to_numpy(); gap = pd.Series(np.abs(o[1:]-c[:-1]), index=mi[1:])
print("median |M1 open-prevclose| by yr", gap.groupby(gap.index.year).median().round(3).to_dict())
# diff by risk in ATR-ish via risk quantiles within era
t["era"] = np.where(t.yr<=2018, "16-18", "19+")
t["rq"] = t.groupby("era").risk.transform(lambda s: pd.qcut(s, 4, labels=False))
print(t.groupby(["era","rq"]).agg(n=("d","size"), diff=("d","mean"), risk=("risk","median")).round(3))
# diff where risk is at least 5x the era's median M1 jump
