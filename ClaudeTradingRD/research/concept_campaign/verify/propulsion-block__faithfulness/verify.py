"""Faithfulness/robustness checks for propulsion-block reading a. Scratch only; ledger disabled."""
import os, sys, importlib.util, time
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
import numpy as np, pandas as pd
import concept_lab as cl

spec = importlib.util.spec_from_file_location(
    "pb", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a/propulsion-block.py")
pb = importlib.util.module_from_spec(spec); spec.loader.exec_module(pb)

M1 = cl.load_m1()
which = sys.argv[1:] or ["all"]


def show(tag, ev, **kw):
    t = time.time()
    res = cl.trade_test(ev, max_hold=kw.pop("hold", "150min"), n_boot=kw.pop("n_boot", 2000), **kw)
    b = res.get("blocks") or {}
    bl = " ".join(f"{k}:{v['diff']:+.3f}" for k, v in b.items())
    h = res["halves"]
    print(f"{tag:42s} n={res['n']:6d} diff={res['diff']:+.4f} [{res['ci_lo']:+.4f},{res['ci_hi']:+.4f}] "
          f"p={res['p']:.3f} {res['verdict']:12s} H1={h['H1']['diff']:+.3f} H2={h['H2']['diff']:+.3f} | {bl} "
          f"| ties r/c {res['ties']['real_ambiguous']:.3f}/{res['ties']['control_ambiguous']:.3f} "
          f"ovl={res['ctrl_overlap']:.3f} ({time.time()-t:.0f}s)", flush=True)
    return res


def base(kind="low", **over):
    old = {k: getattr(pb, k) for k in over}
    for k, v in over.items():
        setattr(pb, k, v)
    try:
        return pb.detect(M1, kind)
    finally:
        for k, v in old.items():
            setattr(pb, k, v)


if "all" in which or "repro" in which:
    ev = base()
    r = show("repro a (low)", ev)
    show("a + ctrl_tod_tol_min=30", ev, ctrl_tod_tol_min=30)
    show("a hold_basis=bars", ev, hold_basis="bars")

if "all" in which or "params" in which:
    for over in ({"W_RETRACE": 10}, {"W_RETRACE": 40}, {"W_PB": 10}, {"W_PB": 40},
                 {"FILL_BARS": 60}, {"FILL_BARS": 300}, {"MAX_WAIT": 5}):
        show(f"a {over}", base(**over))
    show("a 15m hold 300min", base(), hold="300min")
    show("a TF5m fill50 hold50", base(TF="5min", FILL_BARS=50), hold="50min")
    show("a TF5m fill150 hold150", base(TF="5min"), hold="150min")
    show("a TF1h fill600 hold10h", base(TF="1h", FILL_BARS=600), hold="10h")
