import pickle, numpy as np, pandas as pd
P = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/trend-entry-options__faithfulness/placebo.pkl"
d = pickle.load(open(P, "rb"))
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python"); import concept_lab as cl
b = cl.bars("15min"); atr = (b.high-b.low).rolling(96, min_periods=20).mean(); atr.index = pd.DatetimeIndex(b.close_time).tz_convert("UTC")
def prep(name):
    ev, t = d[name]
    t = t.copy(); t["x"] = t.net_R - t.ctrl_mean_R; t["x5050"] = t.net_R_5050 - t.ctrl_mean_R_5050
    a = atr.reindex(pd.DatetimeIndex(t.decision_time).tz_convert("UTC")).to_numpy()
    t["sa"] = t.risk / a
    return t.dropna(subset=["sa"])
base = prep("fade_notrend"); edges = np.quantile(base.sa, [0, .2, .4, .6, .8, 1]); edges[0]=0; edges[-1]=1e9
for name in ["real", "counter_trend_mirror", "fade_all", "fade_notrend"]:
    t = prep(name); q = pd.cut(t.sa, edges, labels=False)
    g = t.groupby(q).agg(n=("x","size"), diff=("x","mean"))
    print(name, "overall", round(t.x.mean(),4), "5050", round(t.x5050.mean(),4), "share per base-quintile", (g.n/g.n.sum()).round(3).tolist(), "diff", g["diff"].round(3).tolist())
# reweight: expected diff of fade_notrend if it had real's stop-size mix
r = prep("real"); qr = pd.cut(r.sa, edges, labels=False); qb = pd.cut(base.sa, edges, labels=False)
w = qr.value_counts(normalize=True).sort_index(); bd = base.groupby(qb).x.mean()
print("fade_notrend reweighted to real stop mix:", round(float((w*bd).sum()),4), " real:", round(r.x.mean(),4))
cm = prep("counter_trend_mirror"); qc = pd.cut(cm.sa, edges, labels=False)
print("counter reweighted to real mix:", round(float((w*cm.groupby(qc).x.mean()).sum()),4))
# real minus base per-bin excess, with day-bootstrap
r["exc"] = r.x - bd.reindex(qr).to_numpy()
day = pd.DatetimeIndex(r.decision_time).tz_convert("America/New_York").floor("D")
gm = r.groupby(day).exc.agg(["sum","size"]); rng = np.random.default_rng(1); k=len(gm)
bs = [ (lambda s: s["sum"].sum()/s["size"].sum())(gm.iloc[rng.integers(0,k,k)]) for _ in range(2000)]
print("real excess over stop-matched fade_notrend:", round(r.exc.mean(),4), np.round(np.quantile(bs,[.025,.975]),4))
yr = pd.DatetimeIndex(r.decision_time).year
print("excess by year", r.groupby(yr).exc.mean().round(3).to_dict())
print("real diff by year", r.groupby(yr).x.mean().round(3).to_dict())
