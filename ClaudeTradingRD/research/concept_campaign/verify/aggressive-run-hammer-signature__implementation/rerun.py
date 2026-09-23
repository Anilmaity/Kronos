import sys, importlib.util
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a/aggressive-run-hammer-signature.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
cl = m.cl
ev = cl.cache_frame(f"hammer_{m.TF}_lb{m.LOOKBACK}_w{m.WICK_CUT}", lambda: m.detect(cl.load_m1()))
print(len(ev), cl.frame_fingerprint(ev))
res = cl.trade_test(ev, max_hold=m.MAX_HOLD, claim="+", ctrl_tod_tol_min=m.TOD_TOL, keep_trades=True)
for k in ["n","avg_R","diff","ci_lo","ci_hi","verdict","ties","halves"]:
    print(k, res[k] if k!="halves" else {h:res[k][h]["diff"] for h in ("H1","H2")})
tr = res["_trades"]; print(tr.columns.tolist()); print(tr.head())
tr.to_pickle("orig_trades.pkl"); ev.to_pickle("orig_events.pkl")
