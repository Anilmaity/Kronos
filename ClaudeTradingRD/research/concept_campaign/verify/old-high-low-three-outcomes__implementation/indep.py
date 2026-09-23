"""Independent re-implementation of old-high-low-three-outcomes from the YAML (verification only)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np

K=3
def detect(m1, first_touch_strict=True):
    # own 15m bars via resample on NY-agnostic UTC grid (15m aligns identically)
    b = m1[["open","high","low","close"]].resample("15min", label="left", closed="left").agg(
        {"open":"first","high":"max","low":"min","close":"last"}).dropna()
    last_m1 = m1.index.to_series().resample("15min", label="left", closed="left").max().reindex(b.index)
    ctime = b.index + pd.Timedelta(minutes=15)
    # own prior-day levels: group m1 by trading day (18:00 NY roll)
    td_m1 = cl.trading_day(m1.index)
    g = m1.groupby(td_m1).agg(high=("high","max"), low=("low","min"))
    days = g.index
    prev = g.shift(1)
    tdb = cl.trading_day(b.index)
    PH = prev["high"].reindex(tdb).to_numpy(float); PL = prev["low"].reindex(tdb).to_numpy(float)
    o,h,l,c = (b[x].to_numpy(float) for x in "open high low close".split())
    n=len(b); out=[]
    tdv = np.asarray(tdb.asi8)
    for side in (1,-1):
        L = PH if side>0 else PL
        done=set()
        for i in range(n):
            if not np.isfinite(L[i]) or tdv[i] in done: continue
            lv=L[i]
            hit = h[i]>lv if side>0 else l[i]<lv
            if not hit: continue
            done.add(tdv[i])        # first interaction of the day with this level
            if first_touch_strict and not (o[i]<=lv if side>0 else o[i]>=lv):
                continue            # gapped beyond: not a 'return' to the level
            beyond = c[i]>lv if side>0 else c[i]<lv
            if not beyond:
                out.append((ctime[i], -side, h[i] if side>0 else l[i], 3)); continue
            j=None
            for m in range(i+1, min(i+1+K, n)):
                if tdv[m]!=tdv[i]: break
                if (c[m]<lv) if side>0 else (c[m]>lv): j=m; break
            if j is not None:
                st = h[i:j+1].max() if side>0 else l[i:j+1].min()
                out.append((ctime[j], -side, st, 2))
            elif i+K<n and all(tdv[i+k]==tdv[i] for k in range(1,K+1)):
                m=i+K
                st = l[i+1:m+1].min() if side>0 else h[i+1:m+1].max()
                if (st<c[m]) if side>0 else (st>c[m]):
                    out.append((ctime[m], side, st, 1))
    ev=pd.DataFrame(out, columns=["decision_time","direction","stop_px","branch"])
    ev["available_at"]=ev["decision_time"]; ev["rr"]=2.0
    return ev.sort_values(["decision_time","direction"]).reset_index(drop=True)

def s(tag,res): print(tag, res['n'], round(res['diff'],4), [round(res['ci_lo'],4), round(res['ci_hi'],4)], round(res['p'],3), res['verdict'], {h:round(v['diff'],3) for h,v in res['halves'].items() if isinstance(v,dict)}, 'ctrl',round(res['control']['avg_R'],3),'real',round(res['avg_R'],3), res['ties'].get('verdict_stop_first'))
m1=cl.load_m1()
for strict in (True, False):
    ev=detect(m1, strict)
    print('strict',strict,len(ev), ev.branch.value_counts().to_dict())
    s('INDEP', cl.trade_test(ev.drop(columns='branch'), max_hold='150min'))
    if strict: ev.to_pickle('indep_events.pkl')
