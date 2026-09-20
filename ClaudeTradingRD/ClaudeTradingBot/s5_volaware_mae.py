"""
s5_volaware_mae.py — Max Adverse Excursion analysis to find the safe stop distance.

Question: among trades that EVENTUALLY hit target, how far (in units of overshoot ov) do
they draw down first? If winners rarely exceed ~X*ov drawdown, a stop at X*ov cuts the
loss tail WITHOUT converting winners to losers. This is the real overshoot-aware stop.

We re-simulate with NO stop (only target / time-stop) and record MAE for each outcome.
"""
import os, numpy as np
import bot.snap_ict_maker as M

USD = 10.0
path = os.path.join(os.path.dirname(__file__), "reports", "xau_m5_3y.csv")
t, o, c, h, l = M.load(path)
bias = M.daily_ict_bias(t, c, h, l)
n = len(c)
hour, mv, sd, rv, thr = M.indicators(t, c, h, l)

rows = []
i = M.W + 1
while i < n - 2:
    ok = (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i] > 0 and M.SESSION(hour[i])
          and np.isfinite(rv[i]) and np.isfinite(thr[i]) and rv[i] < thr[i] and abs(mv[i]) >= M.K*sd[i])
    if not ok: i += 1; continue
    up = mv[i] > 0; side = -1 if up else 1; ov = abs(mv[i])
    if bias[i] == 0 or np.sign(side) != bias[i]: i += 1; continue
    L = c[i] + (M.OFFSET*sd[i] if up else -M.OFFSET*sd[i]); fj = None
    for j in range(i+1, min(i+1+M.FILL_WIN, n)):
        if up and h[j] >= L: fj = j; break
        if (not up) and l[j] <= L: fj = j; break
    if fj is None: i += 1; continue
    entry = L
    target = entry - M.TARGET_F*ov if up else entry + M.TARGET_F*ov
    # simulate WITHOUT stop: target or time-stop only; track MAE (adverse move in price)
    ex = None; mk = False; mae = 0.0; jend = fj
    for j in range(fj+1, min(fj+1+M.TIME, n)):
        jend = j
        adverse = (h[j]-entry) if up else (entry-l[j])   # how far it went against us
        if adverse > mae: mae = adverse
        if up and l[j] <= target: ex = target; mk = True; break
        if (not up) and h[j] >= target: ex = target; mk = True; break
    if ex is None: ex = c[min(fj+M.TIME, n-1)]
    pnl_nostop = (ex-entry)*side + M.HALF + (M.HALF if mk else -M.HALF)
    rows.append(dict(ov=ov, mae=mae, mae_in_ov=mae/ov if ov>0 else 0,
                     hit_target=mk, pnl_nostop=pnl_nostop, year=t[i][:4]))
    i = jend + 1

mae_ov = np.array([r["mae_in_ov"] for r in rows])
hit = np.array([r["hit_target"] for r in rows])
ov = np.array([r["ov"] for r in rows])

print(f"=== MAE analysis (NO-STOP sim, n={len(rows)}) ===\n")

print("Among trades that HIT TARGET — drawdown first reached (in units of overshoot ov):")
w = mae_ov[hit]
for q in (50, 75, 90, 95, 99, 100):
    print(f"  p{q:>3}: {np.percentile(w, q):.2f} x ov")
print(f"  -> a stop at K*ov keeps a winner only if its MAE < K*ov")

print("\nIf we place stop at S*ov, what % of CURRENT target-winners survive (MAE<S*ov)?")
for S in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
    survive = (w < S).mean()
    print(f"  stop {S:.2f}*ov : {100*survive:5.1f}% of winners survive")

print("\nSame, split by overshoot size (big overshoots = the profitable tail):")
big = ov >= np.quantile(ov, 0.75)
for lab, m in [("small/mid ov", ~big), ("big ov (top25%)", big)]:
    ww = mae_ov[hit & m]
    print(f"  {lab}: winner MAE p50={np.percentile(ww,50):.2f} p90={np.percentile(ww,90):.2f} "
          f"p95={np.percentile(ww,95):.2f} x ov")
