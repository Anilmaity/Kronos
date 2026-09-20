"""Deliverable: the OVERFIT lower-TF scalp as a runnable system with a realistic
(non-overlapping) equity curve from $5,000 — built to reproduce the live account's
high WR + profit. Overfitting is intentional (user directive). Saves the model.
"""
import csv, datetime as dt, pickle
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
import m1_overfit_scalp as M   # reuse load/build + constants

bars = M.load(M.CSV)
X, pnl, valid, fn, ts = M.build(bars)
t = [b[0] for b in bars]; c = [b[4] for b in bars]
idx = np.where(valid)[0]
Xv = X[idx]; y = (pnl[idx] > 0).astype(int)

clf = HistGradientBoostingClassifier(max_iter=600, max_depth=None, learning_rate=0.1,
                                     l2_regularization=0.0, min_samples_leaf=5,
                                     max_leaf_nodes=255, random_state=0)
clf.fit(Xv, y)
proba_full = np.full(len(bars), -1.0)
proba_full[idx] = clf.predict_proba(Xv)[:, 1]
with open("reports/overfit_scalp_model.pkl", "wb") as f:
    pickle.dump({"model": clf, "features": fn, "TP": M.TP, "SL": M.SL,
                 "HOLD": M.HOLD, "LB": M.LB}, f)

# pnl per candidate bar is already the realized fade-scalp P&L (0.1 lot). Walk with
# NON-OVERLAP: enter when flat & confidence>=thr, then skip HOLD bars (position busy).
def run(thr, start=5000.0):
    eq = start; peak = eq; mdd = 0; trades = []; busy_until = -1
    for i in idx:
        if i <= busy_until:
            continue
        if proba_full[i] >= thr and np.isfinite(pnl[i]):
            eq += pnl[i]; peak = max(peak, eq); mdd = min(mdd, eq - peak)
            trades.append((t[i], pnl[i], eq)); busy_until = i + M.HOLD
    return trades, eq, mdd

print(f"{'thr':>5} {'trades':>7} {'WR':>6} {'start$':>7} {'end$':>9} {'net$':>9} {'maxDD$':>8}")
for thr in (0.75, 0.80, 0.85, 0.90):
    tr, eq, mdd = run(thr)
    if not tr: continue
    wr = 100 * sum(1 for _, p, _ in tr if p > 0) / len(tr)
    net = eq - 5000
    print(f"{thr:>5} {len(tr):>7} {wr:>5.1f}% {5000:>7} {eq:>9.0f} {net:>+9.0f} {mdd:>8.0f}")

# detailed view at a threshold that mirrors the live account's scale/feel
tr, eq, mdd = run(0.85)
import collections
bymon = collections.OrderedDict()
for tt, p, e in tr:
    bymon.setdefault(tt.strftime("%Y-%m"), [0, 0, 0.0])
    bymon[tt.strftime("%Y-%m")][0] += 1
    bymon[tt.strftime("%Y-%m")][1] += (1 if p > 0 else 0)
    bymon[tt.strftime("%Y-%m")][2] += p
wr = 100 * sum(1 for _, p, _ in tr if p > 0) / len(tr)
print(f"\n=== OVERFIT SCALP SYSTEM @ conf>=0.85 (IN-SAMPLE reproduction) ===")
print(f"  $5,000 -> ${eq:,.0f}  net ${eq-5000:+,.0f}  over {len(tr)} trades  WR {wr:.1f}%  maxDD ${mdd:,.0f}")
print(f"  (live account for reference: $5,000 -> $5,452, 92.5% WR, +$452)")
print("  by month: " + "  ".join(f"{m}:{v[1]}/{v[0]}={100*v[1]/v[0]:.0f}% ${v[2]:+.0f}" for m, v in bymon.items()))
print("  model saved -> reports/overfit_scalp_model.pkl")
