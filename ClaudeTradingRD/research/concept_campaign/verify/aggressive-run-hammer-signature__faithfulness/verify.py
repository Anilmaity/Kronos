import os, sys
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

m1 = cl.load_m1()
b = cl.build_bars(m1, "5min")
o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
body = np.abs(c - o)
ct = pd.DatetimeIndex(b["close_time"])

def mk(hm, sh, extra_filter=None):
    both = hm & sh; hm = hm & ~both; sh = sh & ~both
    ih, is_ = np.flatnonzero(hm), np.flatnonzero(sh)
    out = pd.concat([pd.DataFrame({"decision_time": ct[ih], "direction": 1, "stop_px": l[ih]}),
                     pd.DataFrame({"decision_time": ct[is_], "direction": -1, "stop_px": h[is_]})]
                    ).sort_values("decision_time").reset_index(drop=True)
    out["available_at"] = out["decision_time"]; out["rr"] = 2.0
    return out

def run(name, ev):
    r = cl.trade_test(ev, max_hold="50min", claim="+", ctrl_tod_tol_min=30, keep_trades=True)
    tr = r["_trades"]
    g = np.isfinite(tr["ctrl_mean_R"].to_numpy())
    d5 = np.nanmean(tr["net_R_5050"].to_numpy()[g]) - np.nanmean(tr["ctrl_mean_R_5050"].to_numpy()[g])
    bl = {k: round(v["diff"], 4) for k, v in (r.get("blocks") or {}).items()}
    print(f"{name:28s} n={r['n']:6d} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] "
          f"H1={r['halves']['H1']['diff']:+.4f} H2={r['halves']['H2']['diff']:+.4f} {r['verdict']} "
          f"avgR={r['avg_R']:+.4f} d5050={d5:+.4f} ovl={r['ctrl_overlap']:.3f} blocks={bl}", flush=True)
    return r

for LB in [20]:
    lo_prev = pd.Series(l).rolling(LB).min().shift(1).to_numpy()
    hi_prev = pd.Series(h).rolling(LB).max().shift(1).to_numpy()
    base_h = (l < lo_prev) & (c > lo_prev); base_s = (h > hi_prev) & (c < hi_prev)
    orig_h = base_h & ((o - l) > body); orig_s = base_s & ((h - o) > body)
    # share of red hammers / green shooters (where the wick test is vacuous)
    print("orig hammers", orig_h.sum(), "red-bodied share", (orig_h & (c < o)).sum() / orig_h.sum())
    print("orig shooters", orig_s.sum(), "green-bodied share", (orig_s & (c > o)).sum() / orig_s.sum())
    print("share failing true-wick test", ((orig_h & ~((np.minimum(o,c)-l) > body)).sum() + (orig_s & ~((h-np.maximum(o,c)) > body)).sum())/(orig_h.sum()+orig_s.sum()))
    run("orig_reproduce", mk(orig_h, orig_s))
    # faithful hammer: lower wick (min(o,c)-l) > body ; shooter: upper wick > body
    run("true_wick>body", mk(base_h & ((np.minimum(o,c)-l) > body), base_s & ((h-np.maximum(o,c)) > body)))
    # classic hammer: lower wick >= 2x body
    run("true_wick>=2body", mk(base_h & ((np.minimum(o,c)-l) >= 2*body), base_s & ((h-np.maximum(o,c)) >= 2*body)))
    # candle color matches reversal (green hammer / red shooter) with orig wick rule
    run("orig_color_aligned", mk(orig_h & (c > o), orig_s & (c < o)))
    run("orig_color_opposed", mk(orig_h & (c < o), orig_s & (c > o)))
    # no shape gate: any run-and-return close back inside
    run("no_shape_gate", mk(base_h, base_s))
for LB in [10, 40]:
    lo_prev = pd.Series(l).rolling(LB).min().shift(1).to_numpy()
    hi_prev = pd.Series(h).rolling(LB).max().shift(1).to_numpy()
    run(f"orig_lb{LB}", mk((l < lo_prev) & (c > lo_prev) & ((o - l) > body), (h > hi_prev) & (c < hi_prev) & ((h - o) > body)))
