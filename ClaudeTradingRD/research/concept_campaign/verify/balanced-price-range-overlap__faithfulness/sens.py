"""Faithfulness/robustness probes of balanced-price-range-overlap reading a.
Ledger disabled: verification, not campaign hypotheses."""
import os, sys, importlib.util, pickle, json
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
SRC = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05b/balanced-price-range-overlap.py"
sys.path.insert(0, str(Path(SRC).parent))
spec = importlib.util.spec_from_file_location("bpr", SRC); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
HERE = Path(__file__).parent
m1 = cl.load_m1()

def build(tf="15min", pair=20, window="24h"):
    f = HERE / f"ev_{tf}_{pair}_{window}.pkl"
    if f.exists(): return pd.read_pickle(f)
    M.TF, M.PAIR_BARS, M.WINDOW = tf, pair, pd.Timedelta(window)
    ev = M.detect(m1); ev.to_pickle(f); return ev

def run(label, ev, **kw):
    kw.setdefault("max_hold", "150min")
    r = cl.trade_test(ev, cluster="bpr_id", n_boot=500, keep_trades=True, **kw)
    tr = r.get("_trades")
    yr = {}
    if tr is not None:
        t = pd.DatetimeIndex(tr["decision_time"])
        d = tr["net_R"].to_numpy() - tr["ctrl_mean_R"].to_numpy()
        s = pd.Series(d, index=t.year)
        yr = s.groupby(level=0).mean().round(3).to_dict()
    b = {k: round(v["diff"], 3) for k, v in (r.get("blocks") or {}).items()}
    h = {k: round(r["halves"][k]["diff"], 3) for k in ("H1", "H2")} if r.get("halves") else {}
    print(f"{label:34s} n={r['n']:6d} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] {r['verdict']:12s} H={h} B={b}", flush=True)
    return r, yr

if __name__ == "__main__":
    base = build()
    r, yr = run("baseline (repro)", base)
    print("  per-year diff:", yr)
    print("  ties:", r["ties"], "ctrl_overlap", r["ctrl_overlap"])
    run("ctrl_tod_tol_min=30", base, ctrl_tod_tol_min=30)
    run("hold_basis=bars", base, hold_basis="bars")
    run("correct_side only (rule 4)", base[base.correct_side].reset_index(drop=True))
    run("wrong_side only", base[~base.correct_side].reset_index(drop=True))
    for p in (2, 5, 10, 40):
        run(f"pair_bars={p}", build(pair=p))
    for w in ("4h", "12h"):
        run(f"window={w}", build(window=w))
    for tf in ("5min", "1h"):
        run(f"tf={tf} (pair 20)", build(tf=tf), max_hold={"5min": "50min", "1h": "10h"}[tf])
