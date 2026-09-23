import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
o = pd.read_parquet("orig_events.parquet"); e = pd.read_parquet("indep_events.parquet")
C=["decision_time","available_at","direction","stop_px","rr"]
for nm, ev in (("orig", o), ("indep", e)):
    out=[]
    for s in range(1, 21):
        r = cl.trade_test(ev[C], max_hold="150min", seed=s, n_boot=200)
        out.append((r["diff"], r["control"]["avg_R"], r["verdict"]))
    df = pd.DataFrame(out, columns=["diff","ctrl","verdict"])
    print(nm, "diff mean %.4f sd %.4f min %.4f max %.4f" % (df['diff'].mean(), df['diff'].std(), df['diff'].min(), df['diff'].max()), df.verdict.value_counts().to_dict())
