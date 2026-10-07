"""u1007a: is the gate diff a stop-distance / clock composition effect? Stratify yes vs no by
year x NY hour x direction x risk decile (deciles within year, pooled arms). Ledger redirected."""
import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ["CONCEPT_LAB_LEDGER"] = str(HERE / "wtt_u1007a_impl_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl  # noqa: E401,E402

ev = pd.read_pickle(HERE / "wtt_u1007a_impl_events.pkl")
r = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold="10h", keep_trades=True)
tr = r["_trades"]
tr["adj"] = tr.net_R - tr.ctrl_mean_R
tr = tr[np.isfinite(tr.adj)].copy()
t = pd.DatetimeIndex(tr.decision_time)
tr["yr"] = t.year
tr["hr"] = t.tz_convert("America/New_York").hour
tr["day"] = np.asarray(cl.trading_day(t))
tr["rq"] = tr.groupby("yr").risk.transform(lambda s: pd.qcut(s, 10, labels=False, duplicates="drop"))
print("adj by risk decile (pooled years):")
print(tr.groupby(["rq", "gate"]).adj.mean().unstack().round(4).assign(
      n_yes=tr[tr.gate].groupby("rq").size()))


def strat(col, keys):
    g = tr.groupby(keys + ["gate"])[col].agg(["sum", "count"]).unstack("gate")
    g = g.dropna()
    yes_m = g[("sum", True)] / g[("count", True)]
    no_m = g[("sum", False)] / g[("count", False)]
    w = g[("count", True)]
    return float((w * (yes_m - no_m)).sum() / w.sum()), int(w.sum())


for keys in (["yr"], ["yr", "hr"], ["yr", "rq"], ["yr", "hr", "direction"], ["yr", "hr", "direction", "rq"]):
    print(keys, "adj diff %+.4f (yes n %d)" % strat("adj", keys), "| raw R diff %+.4f" % strat("net_R", keys)[0])

# day-block bootstrap of the fully stratified raw-R diff
keys = ["yr", "hr", "direction", "rq"]
tr["cell"] = tr.groupby(keys).ngroup()
days = np.unique(tr.day)
dmap = {d: i for i, d in enumerate(days)}
tr["di"] = tr.day.map(dmap)
rng = np.random.default_rng(1)
G = tr[["di", "cell", "gate", "net_R", "adj"]].to_numpy()
byday = [G[G[:, 0] == i] for i in range(len(days))] if False else None
idx_by_day = tr.groupby("di").indices
out = {"net_R": [], "adj": []}
for b in range(400):
    pick = rng.integers(0, len(days), len(days))
    rows = np.concatenate([idx_by_day[i] for i in pick])
    s = tr.iloc[rows]
    for col in out:
        g = s.groupby(["cell", "gate"])[col].agg(["sum", "count"]).unstack("gate").dropna()
        w = g[("count", True)]
        out[col].append(float((w * (g[("sum", True)] / w - g[("sum", False)] / g[("count", False)])).sum() / w.sum()))
for col, v in out.items():
    print(f"fully stratified {col}: CI [{np.percentile(v, 2.5):+.4f}, {np.percentile(v, 97.5):+.4f}] (400 day-block draws)")
