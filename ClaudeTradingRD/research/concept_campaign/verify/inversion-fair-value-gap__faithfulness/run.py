import os, sys, json, importlib.util, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(HERE, "verify_ledger.jsonl")   # keep verification out of campaign ledger
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl
import numpy as np, pandas as pd
SCRIPT = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04a/inversion-fair-value-gap.py"
spec = importlib.util.spec_from_file_location("ifvg", SCRIPT); mod = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.dirname(SCRIPT)); spec.loader.exec_module(mod)
m1 = cl.load_m1()
KEYS = ("verdict", "n", "diff", "ci_lo", "ci_hi", "p", "mde", "ctrl_overlap")
def show(tag, res):
    d = {k: (round(res[k], 4) if isinstance(res.get(k), float) else res.get(k)) for k in KEYS}
    d["H1"] = round(res["halves"]["H1"]["diff"], 4); d["H2"] = round(res["halves"]["H2"]["diff"], 4)
    d["blocks"] = [round(v["diff"], 4) for v in res["blocks"].values()]
    d["ties"] = {k: round(v, 4) for k, v in res["ties"].items() if isinstance(v, float)}
    d["exp"] = {k: round(v, 1) for k, v in res["exposure_bars"].items() if isinstance(v, float)}
    print(tag, json.dumps(d), flush=True)
    return d
out = {}
def ev_for(maxw=12, retest=16):
    fn = os.path.join(HERE, f"ev_w{maxw}_r{retest}.pkl")
    if os.path.exists(fn): return pd.read_pickle(fn)
    mod.MAXW, mod.B_RETEST = maxw, retest
    t = time.time(); ev = mod.detect_b(m1); ev.to_pickle(fn); print("built", maxw, retest, len(ev), round(time.time()-t,1), flush=True)
    mod.MAXW, mod.B_RETEST = 12, 16
    return ev
ev = ev_for()
print("fp", cl.frame_fingerprint(ev), len(ev))
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
out["base"] = show("base", res)
tr = res["_trades"]; tr.to_pickle(os.path.join(HERE, "base_trades.pkl")); print(tr.columns.tolist())
for tag, kw in [("tod30", dict(ctrl_tod_tol_min=30)), ("bars", dict(hold_basis="bars")), ("m1grid", dict(ctrl_grid="m1"))]:
    out[tag] = show(tag, cl.trade_test(ev, max_hold="150min", **kw))
for maxw, rt in [(6,16),(24,16),(12,8),(12,32),(12,64),(3,16)]:
    e = ev_for(maxw, rt)
    out[f"w{maxw}_r{rt}"] = show(f"w{maxw}_r{rt}", cl.trade_test(e, max_hold="150min"))
for hold in ["60min", "300min"]:
    out[f"hold{hold}"] = show(f"hold{hold}", cl.trade_test(ev, max_hold=hold))
json.dump(out, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
