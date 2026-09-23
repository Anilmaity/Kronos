import os, sys, json
V = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/point-of-interest__faithfulness"
os.environ["CONCEPT_LAB_LEDGER"] = V + "/verify_ledger.jsonl"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
import importlib.util
spec = importlib.util.spec_from_file_location("poi", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b/point-of-interest.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
cl, np, pd = mod.cl, mod.np, mod.pd
ev = mod.detect(cl.load_m1())
print("fp", cl.frame_fingerprint(ev), len(ev), ev.poi_a.mean())
an = pd.read_pickle(V + "/annot.pkl")
assert (pd.DatetimeIndex(an.decision_time) == pd.DatetimeIndex(ev.decision_time)).all() and (an.poi_a.values == ev.poi_a.values).all()
ev.to_pickle(V + "/ev.pkl")
def run(name, mask, **kw):
    r = cl.gate_test(ev, np.asarray(mask, bool), mask_available_at="decision_time", max_hold="10h", keep_trades=True, **kw)
    bl = {k: round(v["diff"], 3) for k, v in r["blocks"].items()}
    print(f"{name:28s} fire={r['gate_firing_rate']:.3f} n={r['n']}/{r['n_complement']} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] "
          f"H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} blocks={bl} v={r['verdict']} ovl={r['ctrl_overlap']:.3f} ties={r['ties'].get('verdict_5050')}")
    return r
r = run("repro poi_a", ev.poi_a)
tr = r["_trades"]; tr.to_pickle(V + "/trades.pkl")
nofb = ev.poi_a.values & ~an.fb_branch.values
run("a, fallback->fail", nofb)
run("a, polarity aligned", an.a_aligned.fillna(False).values.astype(bool))
run("a, polarity opposing", an.a_opposing.fillna(True).values.astype(bool))
run("a, tod-held control", ev.poi_a, ctrl_tod_tol_min=30)
run("a, hold_basis bars", ev.poi_a, hold_basis="bars")
run("extreme is range extreme", an.is_range_ext.values)
