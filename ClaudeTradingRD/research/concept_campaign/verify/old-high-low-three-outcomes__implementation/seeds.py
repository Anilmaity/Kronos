import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
ev=pd.read_pickle('orig_events.pkl')
for sd in [1,2,3,4,5,6,7,8]:
    try:
        r=cl.trade_test(ev, max_hold='150min', seed=sd, n_boot=500)
    except Exception as e:
        print('seed knob refused:', e); break
    print(sd, round(r['diff'],4), round(r['ci_lo'],4), round(r['ci_hi'],4), r['verdict'], 'ctrl', round(r['control']['avg_R'],3))
