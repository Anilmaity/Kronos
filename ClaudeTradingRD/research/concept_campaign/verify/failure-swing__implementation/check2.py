import sys, importlib.util
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
spec = importlib.util.spec_from_file_location("fs", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a/failure-swing.py")
fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
orig = fs.detect(cl.load_m1(), "b")
ev = pd.read_pickle("ev.pkl"); f = ev[ev.fail]
a = orig.set_index(["decision_time", "above"]).level
m = f.set_index([pd.DatetimeIndex(f.dt), "above"]).level
j = pd.concat([a.rename("o"), m.rename("m")], axis=1)
print("orig", len(a), "mine", len(m), "both", j.dropna().shape[0], "level mismatch", (abs(j.o-j.m) > 1e-9).sum())
print(j[j.isna().any(axis=1)])
# stratified fail - nonfail with day bootstrap
ev["cell"] = ev.bk.astype(str) + ev.above.astype(str)
days = ev.day.unique(); dmap = {d: i for i, d in enumerate(days)}; ev["di"] = ev.day.map(dmap)
def stat(e):
    g = e.groupby(["cell", "fail"]).hit.agg(["sum", "size"]).unstack()
    r = g["sum"] / g["size"]; w = g["size"][True]
    ok = r.notna().all(1)
    return ((r[True] - r[False])[ok] * w[ok]).sum() / w[ok].sum()
print("stat", stat(ev))
rng = np.random.default_rng(3); bs = []
grp = {k: v for k, v in ev.groupby("di").indices.items()}
for _ in range(300):
    pick = rng.integers(0, len(days), len(days))
    idx = np.concatenate([grp[p] for p in pick])
    bs.append(stat(ev.iloc[idx]))
print("CI", np.percentile(bs, [2.5, 97.5]))
