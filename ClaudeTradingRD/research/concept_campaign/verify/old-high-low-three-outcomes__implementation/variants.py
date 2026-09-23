import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
ev=pd.read_pickle('orig_events.pkl')
tr=pd.read_pickle('orig_trades.pkl')
def s(tag,res): print(tag, res['n'], round(res['diff'],4), [round(res['ci_lo'],4), round(res['ci_hi'],4)], round(res['p'],3), res['verdict'], {h:round(v['diff'],3) for h,v in res['halves'].items() if isinstance(v,dict)}, 'ctrl',round(res['control']['avg_R'],3),'real',round(res['avg_R'],3))
# 1) flipped direction, same stop distance (from actual entry used)
e=ev.copy()
ent=tr.set_index('ev_id')['entry']
dist=(ev['stop_px']-ent.reindex(ev.index)).abs()
e=e.loc[dist.notna()].copy(); e['stop_dist']=dist.dropna(); e=e.drop(columns='stop_px'); e['direction']=-e['direction']
s('FLIPPED', cl.trade_test(e, max_hold='150min'))
# 2) tod-matched control (declarable knob; diagnostic only)
s('TOD30', cl.trade_test(ev, max_hold='150min', ctrl_tod_tol_min=30))
# 3) hold basis bars
s('BARS', cl.trade_test(ev, max_hold='150min', hold_basis='bars'))
