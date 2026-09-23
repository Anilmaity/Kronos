import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
tr = pd.read_pickle("orig_trades.pkl"); ev = pd.read_pickle("indep_events.pkl")
tr = tr.merge(ev[["decision_time","dir","g_spec","g_no_cisd_branch","g_no_extreme_bar_fvg","cpos","epos"]].rename(columns={"dir":"direction"}), on=["decision_time","direction"], how="left")
tr["x"] = tr.net_R - tr.ctrl_mean_R
tr["cat"] = np.where(tr.g_no_cisd_branch, "fvg/swing pass", np.where(tr.g_spec, "cisd-branch pass", "fail"))
tr["half"] = np.where(tr.decision_time < pd.Timestamp("2021-01-01", tz="UTC"), "H1", "H2")
print(len(tr), tr.g_spec.isna().sum(), (tr.gate == tr.g_spec).mean())
print(tr.groupby("cat").x.agg(["count","mean","sem"]))
print(tr.groupby(["half","cat"]).x.agg(["count","mean"]))
def boot(a, b, n=2000, rng=np.random.default_rng(1)):
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return a.mean()-b.mean(), np.percentile(d, [2.5, 97.5])
g = tr.x.to_numpy()
print("spec gate", boot(g[tr.g_spec.to_numpy()], g[~tr.g_spec.to_numpy()]))
m = tr.g_no_cisd_branch.to_numpy(); print("fvg/swing-only gate", boot(g[m], g[~m]))
c = tr.cat.to_numpy(); print("fvg/swing pass vs fail (drop cisd branch)", boot(g[c=="fvg/swing pass"], g[c=="fail"]))
print("cisd pass vs fail", boot(g[c=="cisd-branch pass"], g[c=="fail"]))
# how often does the cisd branch fail? and is its pass tautological?
print(tr.groupby("cat").size() / len(tr))
