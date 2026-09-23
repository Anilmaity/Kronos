"""Context check (not a verdict): short after ANY confirmed 5m STH (stop at it), mirror; vs ITH-only."""
import os, sys
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
b = cl.build_bars(cl.load_m1(), "5min"); h=b.high.to_numpy(); l=b.low.to_numpy(); ct=b.close_time.to_numpy()
rows=[]
for i in range(2,len(b)):
    j=i-1
    if h[j]>h[j-1] and h[j]>h[i]: rows.append((ct[i],-1,h[j]))
    if l[j]<l[j-1] and l[j]<l[i]: rows.append((ct[i],1,l[j]))
ev=pd.DataFrame(rows,columns=["decision_time","direction","stop_px"]); ev["decision_time"]=pd.DatetimeIndex(ev.decision_time).tz_localize("UTC") if pd.DatetimeIndex(ev.decision_time).tz is None else ev.decision_time
ev["available_at"]=ev.decision_time; ev["rr"]=2.0
r=cl.trade_test(ev,max_hold="50min")
print({k:r.get(k) for k in ("n","diff","ci_lo","ci_hi","verdict","verdict_detail")})
