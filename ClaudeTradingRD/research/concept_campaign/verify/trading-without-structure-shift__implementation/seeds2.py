import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
o = pd.read_parquet("orig_events.parquet")
C=["decision_time","available_at","direction","stop_px","rr"]
r = cl.trade_test(o[C], max_hold="150min", seed=20260825, n_boot=200); print("locked", r["diff"])
out=[]
for s in range(100, 160):
    r = cl.trade_test(o[C], max_hold="150min", seed=s, n_boot=200)
    out.append((r["diff"], r["ci_lo"], r["verdict"]))
df = pd.DataFrame(out, columns=["diff","lo","verdict"])
print(df["diff"].describe()); print(df.verdict.value_counts()); print("frac >= 0.0806:", (df['diff']>=0.0805).mean())
