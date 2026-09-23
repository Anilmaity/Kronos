import os, sys, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("CONCEPT_LAB_LEDGER", os.path.join(HERE, "verify_ledger.jsonl"))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
spec = importlib.util.spec_from_file_location("tw", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_04b/trading-without-structure-shift.py")
tw = importlib.util.module_from_spec(spec); spec.loader.exec_module(tw)
m1 = cl.load_m1()
OUT = {}

def summ(name, r, tr=None):
    d = {k: r.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "verdict")}
    d["halves"] = {h: round(v["diff"], 4) for h, v in r["halves"].items() if isinstance(v, dict)}
    d["blocks"] = {h: round(v["diff"], 4) for h, v in (r.get("blocks") or {}).items()}
    d["ties"] = r.get("ties"); d["ctrl_overlap"] = r.get("ctrl_overlap"); d["exp"] = r.get("exposure_bars")
    OUT[name] = d
    print(name, json.dumps(d, default=str)); sys.stdout.flush()

def run(name, ev, **kw):
    kw.setdefault("max_hold", "150min")
    r = cl.trade_test(ev, keep_trades=True, **kw)
    summ(name, r); return r

def detect_with(**g):
    old = {k: getattr(tw, k) for k in g}
    for k, v in g.items(): setattr(tw, k, v)
    try: return tw.detect_a(m1)
    finally:
        for k, v in old.items(): setattr(tw, k, v)

ev0 = detect_with()
r0 = run("ORIG", ev0)
tr = r0["_trades"]
tr["adj"] = tr["net_R"] - tr["ctrl_mean_R"]
tr["adj5050"] = tr["net_R_5050"] - tr["ctrl_mean_R_5050"]
tr["yr"] = pd.DatetimeIndex(tr["decision_time"]).year
print(tr.groupby("yr")["adj"].agg(["count", "mean"]).round(3).to_string())
b2 = (tr["decision_time"] >= "2018-08-22") & (tr["decision_time"] < "2021-04-12")
covid = (tr["decision_time"] >= "2020-02-15") & (tr["decision_time"] < "2020-09-01")
print("ex-B2 adj mean", tr.loc[~b2, "adj"].mean(), "n", (~b2).sum())
print("ex-covid adj mean", tr.loc[~covid, "adj"].mean(), "covid", tr.loc[covid, "adj"].mean(), covid.sum())
print("5050 adj mean", tr["adj5050"].mean())
tr["poi"] = ev0["poi"].to_numpy() if len(ev0) == len(tr) else np.nan
print(tr.groupby("poi")["adj"].agg(["count", "mean"]).round(3).to_string())
print(tr.groupby("direction")["adj"].agg(["count", "mean"]).round(3).to_string())
tr["risk_atr"] = tr["risk"]
print("risk quantiles $", tr["risk"].quantile([.1,.25,.5,.75,.9]).round(2).to_dict())
tr["rq"] = pd.qcut(tr["risk"] / tr["entry"] * 1e4, 4, labels=False)
print(tr.groupby("rq")["adj"].agg(["count", "mean"]).round(3).to_string())
# ctrl sensitivity
run("ORIG_tod30", ev0, ctrl_tod_tol_min=30)
run("ORIG_barsbasis", ev0, hold_basis="bars")
# ex-B2 book through harness
run("ORIG_exB2", ev0[~((ev0.decision_time >= "2018-08-22") & (ev0.decision_time < "2021-04-12")).to_numpy()].reset_index(drop=True))
json.dump(OUT, open(os.path.join(HERE, "v1_out.json"), "w"), default=str, indent=1)
