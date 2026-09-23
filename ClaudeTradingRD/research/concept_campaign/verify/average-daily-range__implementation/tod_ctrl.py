import os, sys
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
ev = pd.read_pickle("ev.pkl")
for kw in ({"ctrl_tod_tol_min":30}, {"hold_basis":"bars"}):
    r = cl.gate_test(ev, "open_adr", mask_available_at="decision_time", max_hold="150min", claim="+", **kw)
    print(kw, r["diff"], r["ci_lo"], r["ci_hi"], r["p"], r["verdict"], r["halves"]["H1"]["diff"], r["halves"]["H2"]["diff"], r["exposure_bars"])
# placebo: hour-matched random masks
tr = pd.read_pickle("trades.pkl")
h = pd.DatetimeIndex(tr.decision_time).tz_convert("America/New_York").hour.to_numpy()
adj = (tr.net_R - tr.ctrl_mean_R).to_numpy(); gate = tr.gate.to_numpy()
rate = pd.Series(gate).groupby(h).mean()
rng = np.random.default_rng(1); ds=[]
for _ in range(2000):
    m = rng.random(len(h)) < rate.reindex(h).to_numpy()
    ds.append(adj[m].mean()-adj[~m].mean())
ds=np.array(ds); obs = adj[gate].mean()-adj[~gate].mean()
print("obs", obs, "hour-matched placebo mean", ds.mean(), "sd", ds.std(), "frac>=obs", (ds>=obs).mean())
