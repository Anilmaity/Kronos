import pandas as pd, numpy as np
V = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/point-of-interest__faithfulness"
an = pd.read_pickle(V + "/annot.pkl"); tr = pd.read_pickle(V + "/trades.pkl")
an["ev_id"] = np.arange(len(an))
print(tr.columns.tolist()[:40])
t = tr.merge(an, on="ev_id", how="left")
t["adj"] = t["net_R"] - t["ctrl_mean_R"]
t = t[np.isfinite(t.adj)]
t["grp"] = np.where(t.fb_branch, "fallback(no FVG,no swing)", np.where(t.poi_a, "FVG/swing pass", "fail"))
t["yr"] = pd.DatetimeIndex(t.decision_time_x if "decision_time_x" in t else t.decision_time).year
print(t.groupby("grp").adj.agg(["count", "mean", "sem"]))
print(t.groupby("reason_y").adj.agg(["count", "mean"]))
print(t.groupby("grp").range_len.describe())
p = t.pivot_table(index="yr", columns="grp", values="adj", aggfunc="mean").round(3)
p["gate_diff"] = t.groupby("yr").apply(lambda d: d[d.poi_a].adj.mean() - d[~d.poi_a].adj.mean()).round(3)
print(p)
print("fallback pass rate among fallback-branch events with a series:", t[t.fb_branch & (t.reason_y!="no FVG, no swing, no opposing series")].poi_a.mean())
t["rl"] = pd.cut(t.range_len, [-1, 2, 4, 6, 8, 10, 14, 50])
print(t.groupby("rl").agg(n=("adj", "size"), adj=("adj", "mean"), pass_rate=("poi_a", "mean")).round(3))
# within range-length buckets, gated minus complement
g = t.groupby("rl").apply(lambda d: pd.Series({"gd": d[d.poi_a].adj.mean() - d[~d.poi_a].adj.mean(), "nc": (~d.poi_a).sum()}))
print(g.round(3))
