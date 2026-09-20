"""
s5_volaware_diag.py — Diagnose the loss tail of snap_ict_maker BEFORE designing a fix.

Methodology (backtest-expert): understand what creates the -$110 tail vs. what creates
the edge, so the vol-aware stop cuts losers WITHOUT cutting the reversions that ARE the edge.

Records per trade: pnl_pt, overshoot(ov), sd, rv, thr, rv/thr ratio, exit_type, hold bars, year.
"""
import os, numpy as np
import bot.snap_ict_maker as M

USD = 10.0
path = os.path.join(os.path.dirname(__file__), "reports", "xau_m5_3y.csv")
t, o, c, h, l = M.load(path)
bias = M.daily_ict_bias(t, c, h, l)

# ---- instrumented copy of M.backtest that records features + exit type ----
def backtest_instrumented(t, o, c, h, l, bias, direction=+1):
    n = len(c)
    hour, mv, sd, rv, thr = M.indicators(t, c, h, l)
    rows = []  # dict per trade
    i = M.W + 1
    while i < n - 2:
        ok = (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i] > 0 and M.SESSION(hour[i])
              and np.isfinite(rv[i]) and np.isfinite(thr[i]) and rv[i] < thr[i] and abs(mv[i]) >= M.K*sd[i])
        if not ok: i += 1; continue
        up = mv[i] > 0; side = -1 if up else 1; ov = abs(mv[i]); want = side*direction
        if bias[i] == 0 or np.sign(want) != bias[i]: i += 1; continue
        L = c[i] + (M.OFFSET*sd[i] if up else -M.OFFSET*sd[i]); fj = None
        for j in range(i+1, min(i+1+M.FILL_WIN, n)):
            if up and h[j] >= L: fj = j; break
            if (not up) and l[j] <= L: fj = j; break
        if fj is None: i += 1; continue
        entry = L
        target = entry - M.TARGET_F*ov if up else entry + M.TARGET_F*ov
        stop   = entry + M.STOP_F*ov   if up else entry - M.STOP_F*ov
        ex = None; mk = False; extype = "time"
        for j in range(fj+1, min(fj+1+M.TIME, n)):
            if up:
                if h[j] >= stop: ex = stop; extype = "stop"; break
                if l[j] <= target: ex = target; mk = True; extype = "target"; break
            else:
                if l[j] <= stop: ex = stop; extype = "stop"; break
                if h[j] >= target: ex = target; mk = True; extype = "target"; break
        if ex is None: ex = c[min(fj+M.TIME, n-1)]
        pnl = (ex-entry)*side + M.HALF + (M.HALF if mk else -M.HALF)
        rows.append(dict(pnl=pnl, ov=ov, sd=sd[i], rv=rv[i], thr=thr[i],
                         ratio=rv[i]/thr[i], extype=extype, year=t[i][:4]))
        i = j + 1
    return rows

rows = backtest_instrumented(t, o, c, h, l, bias)
pnl = np.array([r["pnl"] for r in rows])
ov  = np.array([r["ov"] for r in rows])
ratio = np.array([r["ratio"] for r in rows])
extype = np.array([r["extype"] for r in rows])

print(f"=== SNAP-ICT-MAKER loss-tail diagnosis  (n={len(rows)} trades) ===")
print(f"Net ${pnl.sum()*USD:+,.0f}  WR {100*(pnl>0).mean():.1f}%  mean ${pnl.mean()*USD:+.2f}/trade\n")

print("P&L distribution ($ at 0.10 lot):")
for q in (0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100):
    print(f"  p{q:>3}: ${np.percentile(pnl, q)*USD:>+8.2f}")
print(f"  worst 5 trades: {[f'${x*USD:+.0f}' for x in np.sort(pnl)[:5]]}")

print("\nExit-type breakdown:")
for et in ("target", "stop", "time"):
    m = extype == et
    if m.sum():
        print(f"  {et:<7} n={m.sum():4d} ({100*m.mean():4.1f}%)  "
              f"WR={100*(pnl[m]>0).mean():4.0f}%  net=${pnl[m].sum()*USD:>+7,.0f}  "
              f"mean=${pnl[m].mean()*USD:+.2f}")

print("\nLosers only — what drives loss SIZE?")
los = pnl < 0
print(f"  losers n={los.sum()}  total ${pnl[los].sum()*USD:+,.0f}  mean ${pnl[los].mean()*USD:+.2f}")
# correlation of loss magnitude with overshoot and ratio (losers only)
lossmag = -pnl[los]
print(f"  corr(loss_size, overshoot) = {np.corrcoef(lossmag, ov[los])[0,1]:+.2f}")
print(f"  corr(loss_size, rv/thr)    = {np.corrcoef(lossmag, ratio[los])[0,1]:+.2f}")

print("\nBucket by overshoot size (is the tail concentrated in big overshoots?):")
qs = np.quantile(ov, [0, .25, .5, .75, .9, 1.0])
labels = ["Q1(small)", "Q2", "Q3", "Q4", "top10%"]
edges = [(qs[0], qs[1]), (qs[1], qs[2]), (qs[2], qs[3]), (qs[3], qs[4]), (qs[4], qs[5]+1e-9)]
for lab, (lo, hi) in zip(labels, edges):
    m = (ov >= lo) & (ov < hi)
    if m.sum():
        print(f"  ov {lab:<9} [{lo:5.2f},{hi:5.2f})pt  n={m.sum():4d}  "
              f"WR={100*(pnl[m]>0).mean():4.0f}%  net=${pnl[m].sum()*USD:>+7,.0f}  "
              f"meanLoss=${pnl[m][pnl[m]<0].mean()*USD if (pnl[m]<0).any() else 0:+.0f}")

print("\nBucket by rv/thr ratio (how 'quiet' is quiet enough?):")
for lo, hi in [(0,.4),(.4,.6),(.6,.8),(.8,1.0)]:
    m = (ratio >= lo) & (ratio < hi)
    if m.sum():
        print(f"  ratio [{lo:.1f},{hi:.1f})  n={m.sum():4d}  WR={100*(pnl[m]>0).mean():4.0f}%  "
              f"net=${pnl[m].sum()*USD:>+7,.0f}  mean=${pnl[m].mean()*USD:+.2f}")
