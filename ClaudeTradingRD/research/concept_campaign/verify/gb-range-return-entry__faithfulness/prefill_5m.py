import os, sys, numpy as np, pandas as pd
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prefill_5m_base.py")).read().split("for lab, keep")[0])
for lab, keep in [("drop_anchor_thru", ~thru), ("only_anchor_thru", thru), ("ran_not_thru", ran & ~thru)]:
    e = ev[keep].reset_index(drop=True)
    r = cl.trade_test(e, max_hold="24h", ctrl_tod_tol_min=30)
    print(f"{lab:18s} n={r['n']} diff={r['diff']:+.3f} [{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] p={r['p']:.3f} H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} blocks={ {k: round(v['diff'],3) for k,v in r['blocks'].items()} } {r['verdict']}")
lag = (ev.decision_time - ev.signal_t).dt.total_seconds()/3600
print("hours signal->fill:", lag.describe().round(2).to_dict())
print("hours signal->fill, anchor-thru:", lag[thru].median(), " clean:", lag[~ran].median())
