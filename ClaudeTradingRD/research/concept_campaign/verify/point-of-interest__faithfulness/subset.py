import os, sys
V = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/point-of-interest__faithfulness"
os.environ["CONCEPT_LAB_LEDGER"] = V + "/verify_ledger.jsonl"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
ev = pd.read_pickle(V + "/ev.pkl"); an = pd.read_pickle(V + "/annot.pkl")
keep = ~an.fb_branch.values
e2 = ev[keep].reset_index(drop=True)
for name, kw in [("non-fallback universe", {}), ("non-fallback, tod ctrl", dict(ctrl_tod_tol_min=30))]:
    r = cl.gate_test(e2, "poi_a", mask_available_at="decision_time", max_hold="10h", **kw)
    bl = {k: round(v["diff"], 3) for k, v in r["blocks"].items()}
    print(f"{name}: n={r['n']}/{r['n_complement']} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} {bl} {r['verdict']} {r['verdict_detail']}")
