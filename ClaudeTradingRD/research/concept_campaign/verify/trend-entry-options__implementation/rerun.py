import sys, importlib.util, numpy as np, pandas as pd
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
p='/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b/trend-entry-options.py'
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b')
spec=importlib.util.spec_from_file_location('teo',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import concept_lab as cl
m1=cl.load_m1()
ev=m.detect(m1)
print(len(ev), ev.option.value_counts().to_dict())
ev.to_pickle('orig_events.pkl')
res=cl.trade_test(ev.drop(columns=['option']), max_hold="150min", keep_trades=True, n_boot=500)
for k in ["n","avg_R","diff","ci_lo","ci_hi","verdict","dropped","ties"]: print(k,res.get(k))
res['_trades'].to_pickle('orig_trades.pkl')
print(res['_trades'].columns.tolist())
