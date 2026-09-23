"""Faithfulness/robustness verification for gb-range-return-entry (scratch; not a result)."""
import sys, pickle, os, importlib.util, json
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gbrr", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a/gb-range-return-entry.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
cl = mod.cl
m1 = cl.load_m1()

def run(label, **kw):
    fn = os.path.join(D, f"ev_{label}.pkl")
    if os.path.exists(fn):
        ev = pd.read_pickle(fn)
    else:
        saved = {k: getattr(mod, k) for k in kw}
        for k, v in kw.items(): setattr(mod, k, v)
        try: ev = mod.detect(m1)
        finally:
            for k, v in saved.items(): setattr(mod, k, v)
        ev.to_pickle(fn)
    return ev

def test(label, ev, **tk):
    res = cl.trade_test(ev, max_hold="24h", ctrl_tod_tol_min=30, keep_trades=True, **tk)
    b = {k: round(v["diff"], 3) for k, v in res["blocks"].items()}
    print(f"{label:28s} n={res['n']:5d} diff={res['diff']:+.3f} [{res['ci_lo']:+.3f},{res['ci_hi']:+.3f}] p={res['p']:.3f} "
          f"H1={res['halves']['H1']['diff']:+.3f} H2={res['halves']['H2']['diff']:+.3f} blocks={b} avgR={res['avg_R']:+.3f} {res['verdict']}", flush=True)
    return res

variants = {
  "base": {},
  "N3": dict(N_DISP=3), "N6": dict(N_DISP=6), "N8": dict(N_DISP=8), "N2": dict(N_DISP=2),
  "r1.3": dict(R_DISP=1.3), "r2.0": dict(R_DISP=2.0),
  "d0.5": dict(D_DISP=0.5), "d1.0": dict(D_DISP=1.0),
  "tgt0.705": dict(X_TGT=0.705), "tgt0.79": dict(X_TGT=0.79),
  "sw33": dict(SWING=(3, 3)),
  "tf5m": dict(TF="5min"), "tf1h": dict(TF="1h"),
  "nodisp": dict(R_DISP=0.0, D_DISP=-1e9),
}
which = sys.argv[1:] or list(variants)
out = {}
for lab in which:
    ev = run(lab, **variants[lab])
    r = test(lab, ev)
    out[lab] = {k: r[k] for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict")}
    if lab == "base":
        tr = r["_trades"]; pd.to_pickle(r, os.path.join(D, "base_res.pkl"))
json.dump(out, open(os.path.join(D, "grid_" + "_".join(which)[:60] + ".json"), "w"), indent=1, default=str)
