"""Re-run the original reading b with the ledger redirected (no write_result)."""
import os, sys, importlib.util
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(__file__), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
P = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02a/internal-range-liquidity.py"
spec = importlib.util.spec_from_file_location("irl", P); m = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.dirname(P)); spec.loader.exec_module(m)
ev = m.detect(cl.load_m1())
ev.to_pickle(os.path.join(os.path.dirname(__file__), "orig_events.pkl"))
print("n events", len(ev), "fp", cl.frame_fingerprint(ev))
mkt = cl.get_market(); t = pd.DatetimeIndex(ev.decision_time); d = ev.direction.to_numpy(int)
px0 = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o)-1)]
def hit(times, level, dirs):
    out = np.zeros(len(times), bool)
    for s, side in ((1,"above"),(-1,"below")):
        mm = dirs == s
        if mm.any(): out[mm] = cl.touch(times[mm], level[mm], side, horizon_bars=600)["hit"].to_numpy()
    return out
lvl = ev.ce.to_numpy(float); dist = lvl - px0; obs = hit(t, lvl, d)
for label, kw in (("orig", {}), ("tod30", {"tod_tol_min": 30})):
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, **kw)
    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"); ok = ~tk.isna()
        out = np.full(len(t), np.nan); p = mkt.o[mkt.pos_at_or_after(tk[ok])]
        out[ok] = hit(tk[ok], p + dist[ok], d[ok]); return out
    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="+", predictors=ev)
    print(label, res["n"], round(res["observed_rate"],4), round(res["null_rate"],4), round(res["diff"],4),
          round(res["ci_lo"],4), round(res["ci_hi"],4), res["p"], res["verdict"], res["halves"]["H1"]["diff"], res["halves"]["H2"]["diff"])
np.save(os.path.join(os.path.dirname(__file__), "obs_b.npy"), obs)
