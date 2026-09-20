"""OVERFIT lower-timeframe scalp to reproduce the live account's result (high WR + profit).
Per the user's directive: lower TF like the real trades, overfitting EXPLICITLY ALLOWED,
reproducing the similar result is the priority over generalization.

Method: at each 1-minute bar, simulate a fade-scalp like the real trades (tiny TP, loose
stop, fast time-exit), label it by its realized P&L after costs, then let a HIGH-CAPACITY
model (deep, low-regularization gradient boosting) learn which conditions win and trade only
its predicted winners. With overfitting allowed, the in-sample selection reproduces (and can
exceed) ~90% WR + positive profit. We ALSO print an honest train->forward check so the
overfit nature is explicit.
"""
import csv, datetime as dt
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

CSV = "reports/xau_m1_2026ytd.csv"
SPREAD = 0.25; COMMISSION = 0.05; USD = 10.0  # $/pt at 0.1 lot
TP = 0.8; SL = 4.0; HOLD = 5; LB = 5          # fade-scalp like the real trades (≈59s-5min)


def load(path):
    b = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            b.append((dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                      float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    return b


def build(bars):
    t=[b[0] for b in bars]; h=[b[2] for b in bars]; l=[b[3] for b in bars]; c=np.array([b[4] for b in bars])
    n=len(c); hour=np.array([x.hour for x in t]); minute=np.array([x.minute for x in t])
    def ret(k):
        r=np.full(n,np.nan); r[k:]=c[k:]-c[:-k]; return r
    def vol(k):
        d=np.diff(c,prepend=c[0]); cs=np.cumsum(d*d); v=np.full(n,np.nan); v[k:]=np.sqrt((cs[k:]-cs[:-k])/k); return v
    feats={"r1":ret(1),"r3":ret(3),"r5":ret(5),"r15":ret(15),"r30":ret(30),"r60":ret(60),
           "v5":vol(5),"v15":vol(15),"v60":vol(60),"accel":ret(5)-ret(30)/6,
           "hsin":np.sin(2*np.pi*hour/24),"hcos":np.cos(2*np.pi*hour/24),
           "msin":np.sin(2*np.pi*minute/60)}
    X=np.column_stack([feats[k] for k in feats]); fn=list(feats)
    # label: fade-scalp forward P&L. side = fade the last-LB move.
    pnl=np.full(n,np.nan)
    for i in range(LB, n-HOLD):
        if (t[i+HOLD]-t[i]).total_seconds()>HOLD*60+30: continue
        mv=c[i]-c[i-LB]
        if abs(mv)<0.3: continue                 # need a move to fade
        side=-1 if mv>0 else 1                    # fade: sell after up, buy after down
        entry=c[i]+SPREAD/2*side*-1 if side>0 else c[i]-SPREAD/2  # buy@ask / sell@bid
        entry=c[i]+SPREAD/2 if side>0 else c[i]-SPREAD/2
        tp_px=entry+TP if side>0 else entry-TP
        sl_px=entry-SL if side>0 else entry+SL
        ex=None
        for j in range(i+1,i+1+HOLD):
            if side>0:
                if l[j]<=sl_px: ex=sl_px; break
                if h[j]>=tp_px: ex=tp_px; break
            else:
                if h[j]>=sl_px: ex=sl_px; break
                if l[j]<=tp_px: ex=tp_px; break
        if ex is None:
            cc=c[min(i+HOLD,n-1)]; ex=cc-SPREAD/2 if side>0 else cc+SPREAD/2
        pts=(ex-entry) if side>0 else (entry-ex)
        pnl[i]=pts*USD-COMMISSION
    valid=np.isfinite(pnl) & np.isfinite(X).all(axis=1)
    return X, pnl, valid, fn, np.array([x.timestamp() for x in t])


if __name__=="__main__":
    bars=load(CSV); X,pnl,valid,fn,ts=build(bars)
    idx=np.where(valid)[0]
    Xv=X[idx]; y=(pnl[idx]>0).astype(int); pv=pnl[idx]
    print(f"candidate fade-scalps: {len(idx)}  base win-rate {100*y.mean():.1f}%  base net ${pv.sum():+.0f} (un-selected)")

    # ---- 1) FULL OVERFIT (in-sample, as requested): deep model selects winners ----
    clf=HistGradientBoostingClassifier(max_iter=600, max_depth=None, learning_rate=0.1,
                                        l2_regularization=0.0, min_samples_leaf=5,
                                        max_leaf_nodes=255, random_state=0)
    clf.fit(Xv, y)
    proba=clf.predict_proba(Xv)[:,1]
    for thr in (0.5,0.7,0.85,0.95):
        sel=proba>=thr
        if sel.sum()<10: continue
        net=pv[sel].sum(); wr=100*(pv[sel]>0).mean()
        print(f"  [IN-SAMPLE overfit] conf>={thr}: trades={sel.sum():6d}  WR={wr:.1f}%  net=${net:+,.0f}  exp=${net/sel.sum():+.2f}")

    # ---- 2) Honest forward check: train on first 60%, trade last 40% ----
    split=int(len(idx)*0.6)
    clf2=HistGradientBoostingClassifier(max_iter=600, max_depth=None, learning_rate=0.1,
                                        l2_regularization=0.0, min_samples_leaf=5,
                                        max_leaf_nodes=255, random_state=0)
    clf2.fit(Xv[:split], y[:split])
    pte=clf2.predict_proba(Xv[split:])[:,1]; pnl_te=pv[split:]
    print("\n  [HONEST forward (train 60% -> trade 40%)]:")
    for thr in (0.5,0.7,0.85,0.95):
        sel=pte>=thr
        if sel.sum()<10: continue
        net=pnl_te[sel].sum(); wr=100*(pnl_te[sel]>0).mean()
        print(f"    conf>={thr}: trades={sel.sum():6d}  WR={wr:.1f}%  net=${net:+,.0f}  exp=${net/sel.sum():+.3f}")
