"""Faithfulness/robustness check of fractal-model-c2 reading a (verification only; not written)."""
import sys, json
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import cl, np, pd, OHLC, c2_events, ltf_cisd_inside

def detect(m1, grid="forex", scope="range", gate=True, rev=True):
    b = cl.build_bars(m1, "4h", grid4h=grid)
    b = b[b["n_m1"] >= 60]
    lt = cl.build_bars(m1, "15min")
    c2 = c2_events(b[OHLC], require_reversal_close=rev)
    pos = b.index.get_indexer(pd.DatetimeIndex(c2["time"]))
    rows = b.iloc[pos].copy()
    rows["direction"] = c2["direction"].to_numpy()
    conf = ltf_cisd_inside(b, lt, rows, scope=scope) if gate else np.ones(len(rows), bool)
    prev = b.iloc[np.maximum(pos - 1, 0)]
    bull = (rows["direction"] == "bullish").to_numpy()
    tgt = np.where(bull, np.maximum(prev["high"].to_numpy(), rows["high"].to_numpy()),
                   np.minimum(prev["low"].to_numpy(), rows["low"].to_numpy()))
    ct = pd.DatetimeIndex(rows["close_time"])
    out = pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": np.where(bull, 1, -1),
                        "stop_px": np.where(bull, rows["low"], rows["high"]).astype(float),
                        "target_px": tgt.astype(float)})
    print(f"  raw C2 {len(rows)}, cisd pass {conf.mean():.3f}")
    return out[conf & (pos > 0)].reset_index(drop=True)

m1 = cl.load_m1()
def run(tag, ev, **kw):
    r = cl.trade_test(ev, max_hold="240min", hold_basis="bars", keep_trades=True, **kw)
    tr = r.pop("_trades")
    t = pd.DatetimeIndex(tr["decision_time"]) if "decision_time" in tr else None
    d = tr["net_R"] - tr["ctrl_mean_R"]
    yr = d.groupby(t.year).agg(["mean", "size"]).round(3).to_dict("index") if t is not None else {}
    d5 = (tr["net_R_5050"] - tr["ctrl_mean_R_5050"]).mean() if "net_R_5050" in tr else None
    print(f"{tag}: n={r['n']} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.3f} "
          f"{r['verdict']} H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} "
          f"blocks={[round(v['diff'],3) for v in r['blocks'].values()]} ovl={r['ctrl_overlap']:.3f} d5050={d5}")
    print("   years", {k: v['mean'] for k, v in yr.items()})
    return r, tr

base = detect(m1); r0, tr0 = run("A forex/range (orig)", base)
print("tr cols", list(tr0.columns)[:30])
run("B futures grid", detect(m1, grid="futures"))
run("C utc grid", detect(m1, grid="utc"))
run("D scope=wick", detect(m1, scope="wick"))
run("E no CISD gate", detect(m1, gate=False))
run("F no reversal-close", detect(m1, rev=False))
run("G orig + ctrl_tod_tol 30", base, ctrl_tod_tol_min=30)
