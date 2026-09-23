"""write_result accepts an EDGE built from detector events with NO probe at all, and with
a probe dict that says passed=False (raise_on_fail=False). Uses the a07 leaky book."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
from pathlib import Path
import numpy as np, pandas as pd
import concept_lab as cl
src = open("a07_future_filter_passes_probe.py").read().split("\nev = detect")[0]
ns = {}; exec(src, ns); detect = ns["detect"]
ev = detect(cl.load_m1()); r = cl.trade_test(ev, max_hold="225min")
op = {"rules": ["long first 15m of 4h if up"], "params": {"rr": 1.0}}
ps = {"rr": "declared-before-run: 1R"}
out = Path("scratch_results")
p1 = cl.write_result("gb-levels", "review_noprobe", r, operationalization=op, params_source=ps,
                     script=__file__, results_dir=out)
print("written with NO probe:", p1.name, r["verdict"])
bad = {"sampled": 20, "failures": 20, "passed": False}
p2 = cl.write_result("gb-levels", "review_failedprobe", r, operationalization=op, params_source=ps,
                     script=__file__, results_dir=out, probe=bad)
print("written with FAILED probe:", p2.name, r["verdict"])
