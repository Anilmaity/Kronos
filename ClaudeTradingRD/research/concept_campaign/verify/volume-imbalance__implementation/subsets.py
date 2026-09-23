import os, sys
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
ev = pd.read_pickle("ev_orig.pkl")
m1 = cl.load_m1(); mi = pd.DatetimeIndex(m1.index).tz_convert("UTC")
# approximate risk = |next open - stop|
pos = mi.get_indexer(pd.DatetimeIndex(ev.decision_time), method="bfill")
entry = m1.open.to_numpy()[pos]; ev["risk"] = np.abs(entry - ev.stop_px)
o=m1.open.to_numpy(); c=m1.close.to_numpy(); g=pd.Series(np.abs(o[1:]-c[:-1]), index=mi[1:])
jm = g.groupby(g.index.year).median()
ev["noise"] = ev.decision_time.dt.year.map(jm)
def run(name, sub):
    r = cl.trade_test(sub.drop(columns=["risk","noise"]).reset_index(drop=True), max_hold="150min")
    print(f"{name:32s} n={r['n']:6d} diff={r['diff']:+.4f} CI[{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.3f} {r['verdict']} H1={r['halves']['H1']['diff']:+.3f} H2={r["halves"]["H2"].get("diff",float("nan")):+.3f}")
#run("2019+", ev[ev.decision_time >= "2019-01-01"])
run("2016-2018", ev[ev.decision_time < "2019-01-01"])
for k in (3, 5, 8):
    run(f"risk >= {k}x yearly M1 jump", ev[ev.risk >= k * ev.noise])
    run(f"risk <  {k}x yearly M1 jump", ev[ev.risk < k * ev.noise])
