import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
src=open('indep.py').read().split("m1=cl.load_m1()")[0]
# variant: original-style first touch (only bars that open inside count) but K bars bounded to the day
src2=src.replace("""            done.add(tdv[i])        # first interaction of the day with this level
            if first_touch_strict and not (o[i]<=lv if side>0 else o[i]>=lv):
                continue""","""            if not (o[i]<=lv if side>0 else o[i]>=lv):
                if first_touch_strict: done.add(tdv[i])
                continue
            done.add(tdv[i])""")
assert src2!=src
exec(src2)
m1=cl.load_m1()
ev=detect(m1, False)   # original-style candidate selection, day-bounded K
print(len(ev), ev.branch.value_counts().to_dict())
s('ORIGSEL_DAYBOUND', cl.trade_test(ev.drop(columns='branch'), max_hold='150min'))
o=pd.read_pickle('orig_events.pkl')
key=lambda d: set(zip(d.decision_time, d.direction))
print('orig-only', len(key(o)-key(ev)), 'mine-only', len(key(ev)-key(o)))
d=o[[k not in key(ev) for k in zip(o.decision_time,o.direction)]]
print(d.branch.value_counts().to_dict()); print(d.head(8))
