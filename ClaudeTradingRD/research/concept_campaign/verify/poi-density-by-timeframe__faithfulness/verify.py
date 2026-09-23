"""Faithfulness/robustness check of poi-density-by-timeframe EDGE. Scratch only; ledger disabled."""
import os, sys, json
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.poi import poi_gate

m1 = cl.load_m1()
b = cl.build_bars(m1, "1h"); ohlc = b[["open","high","low","close"]]
ev = cisd_events(ohlc, level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
pos = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
epos = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))

def run_gate(trunc=True, **kw):
    out = []
    for p, et, dr in zip(pos, ev["extreme_time"], ev["direction"]):
        df = ohlc.iloc[:p+1] if trunc else ohlc
        r = poi_gate(df, et, dr, timeframe="1h", setup_type="reversal", **kw)
        out.append((r.passed, r.kind_used, ",".join(r.kinds_found), r.reason, r.detail["last_bar_used"]))
    return pd.DataFrame(out, columns=["ok","kind","found","reason","lbu"])

base = pd.DataFrame({"decision_time": close, "available_at": close,
                     "direction": np.where(ev["direction"]=="bullish",1,-1),
                     "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})
g0 = run_gate(True)
gF = run_gate(False)      # full data (unguarded)
print("orig pass", g0.ok.mean(), "unguarded pass", gF.ok.mean())
print(g0.kind.value_counts(dropna=False)); print(g0.reason.value_counts().head(12))
# guarded (phase-3 style): pass on full data AND resolved at/before the confirm bar
lbu_pos = b.index.get_indexer(pd.DatetimeIndex(gF.lbu))
guard = gF.ok.to_numpy() & (lbu_pos <= pos)
print("guarded pass", guard.mean())

S = {}
def gt(name, mask, evs=base, **kw):
    e = evs.copy(); e["g"] = np.asarray(mask, bool)
    r = cl.gate_test(e, "g", mask_available_at="decision_time", max_hold="10h", **kw)
    S[name] = {k: r.get(k) for k in ("n","n_complement","gate_firing_rate","diff","ci_lo","ci_hi","p","verdict")}
    S[name]["H"] = {h: round(r["halves"][h]["diff"],3) for h in ("H1","H2")}
    S[name]["B"] = {k: round(v["diff"],3) for k, v in (r.get("blocks") or {}).items()}
    S[name]["own"] = r.get("gated_vs_own_control"); S[name]["compl_own"] = r["complement"]["vs_own_control"]
    S[name]["ties"] = r.get("ties",{}).get("verdict_stop_first"); S[name]["ctrl_overlap"] = r.get("ctrl_overlap")
    print(name, json.dumps(S[name], default=str)); sys.stdout.flush()
    return r

gt("A_orig", g0.ok)
gt("A_orig_tod30", g0.ok, ctrl_tod_tol_min=30)
gt("A_orig_bars", g0.ok, hold_basis="bars")
gt("B_guarded_phase3", guard)
# only events where FVG/swing existed (branch 3 excluded)
has = (g0.found != "").to_numpy()
gt("C_fvg_swing_only", g0.ok.to_numpy()[has], evs=base[has].reset_index(drop=True))
# cisd_level branch counted as FAIL (strict: body-hold not observable independent of the CISD itself)
gt("D_branch3_fail", g0.ok.to_numpy() & has)
for nm, kw in [("E_loose_either", dict(require_both_when_both_exist=False)),
               ("F_pol_aligned", dict(polarity="aligned")),
               ("F_pol_opposing", dict(polarity="opposing")),
               ("G_lb20", dict(lookback=20)), ("G_lb60", dict(lookback=60))]:
    g = run_gate(True, **kw); gt(nm, g.ok)
json.dump(S, open(os.path.join(os.path.dirname(__file__), "out.json"), "w"), default=str, indent=1)
