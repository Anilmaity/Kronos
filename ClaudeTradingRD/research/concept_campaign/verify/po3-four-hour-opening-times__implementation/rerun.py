import os, sys, importlib.util
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_own_02a")
import numpy as np, pandas as pd
import concept_lab as cl
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_own_02a/po3-four-hour-opening-times.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
m1 = cl.load_m1()
det = orig.make_detect("futures", 6)
ev = det(m1)
print(len(ev), "long share", (ev.direction==1).mean(), "fp", cl.frame_fingerprint(ev))
res = cl.trade_test(ev, max_hold="4h")
for k in ("n","avg_R","diff","ci_lo","ci_hi","p","mde","verdict","ties","ctrl_overlap","exposure_bars","ci_method"):
    print(k, res.get(k))
print("halves", {h: round(v["diff"],4) for h,v in res["halves"].items() if isinstance(v, dict)})
# bars check
b = cl.build_bars(m1, "4h", grid4h="futures")
ny = cl.to_ny(pd.DatetimeIndex(b.index))
print(pd.Series(ny.hour).value_counts().sort_index())
s6 = b[ny.hour==6]
print(s6.head(3)); print(s6[["close_time"]].tail(3))
print("c2 close NY hours", cl.to_ny(pd.DatetimeIndex(ev.decision_time)).hour.value_counts())
ev.to_pickle("orig_events.pkl")
