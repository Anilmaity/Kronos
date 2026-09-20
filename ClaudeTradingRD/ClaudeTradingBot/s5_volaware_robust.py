"""
s5_volaware_robust.py — Robustness gate for the tighter-stop + const-risk model.
  1. Stop-multiple PLATEAU sweep (not a peak): net, return/DD, per-year positivity.
  2. Slippage stress: spread 0.20 -> 0.30 -> 0.40 pt on the chosen config.
  3. Lot-size sanity: make sure const-risk sizing isn't leaning on the max_lot cap or
     placing stops inside the spread on tiny overshoots.
"""
import os, numpy as np
import bot.snap_ict_maker as M

path = os.path.join(os.path.dirname(__file__), "reports", "xau_m5_3y.csv")
t, o, c, h, l = M.load(path)
bias = M.daily_ict_bias(t, c, h, l)
n = len(c)
hour, mv, sd, rv, thr = M.indicators(t, c, h, l)
PER_PT_PER_LOT = 100.0

def run(sf, risk_usd=15.0, spread=0.20, max_lot=1.0, min_stop_pt=0.0, return_lots=False):
    half = spread/2
    out = []; lots = []; skipped_tiny = 0
    i = M.W + 1
    while i < n - 2:
        ok = (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i] > 0 and M.SESSION(hour[i])
              and np.isfinite(rv[i]) and np.isfinite(thr[i]) and rv[i] < thr[i] and abs(mv[i]) >= M.K*sd[i])
        if not ok: i += 1; continue
        up = mv[i] > 0; side = -1 if up else 1; ov = abs(mv[i])
        if bias[i] == 0 or np.sign(side) != bias[i]: i += 1; continue
        stop_dist = sf*ov
        if stop_dist < min_stop_pt: skipped_tiny += 1; i += 1; continue
        L = c[i] + (M.OFFSET*sd[i] if up else -M.OFFSET*sd[i]); fj = None
        for j in range(i+1, min(i+1+M.FILL_WIN, n)):
            if up and h[j] >= L: fj = j; break
            if (not up) and l[j] <= L: fj = j; break
        if fj is None: i += 1; continue
        entry = L
        target = entry - M.TARGET_F*ov if up else entry + M.TARGET_F*ov
        stop   = entry + sf*ov         if up else entry - sf*ov
        lot = min(risk_usd/(stop_dist*PER_PT_PER_LOT), max_lot); lots.append(lot)
        ex = None; mk = False
        for j in range(fj+1, min(fj+1+M.TIME, n)):
            if up:
                if h[j] >= stop: ex = stop; break
                if l[j] <= target: ex = target; mk = True; break
            else:
                if l[j] <= stop: ex = stop; break
                if h[j] >= target: ex = target; mk = True; break
        if ex is None: ex = c[min(fj+M.TIME, n-1)]
        pnl_pt = (ex-entry)*side + half + (half if mk else -half)
        out.append((pnl_pt*PER_PT_PER_LOT*lot, t[i][:4])); i = j + 1
    if return_lots: return out, np.array(lots), skipped_tiny
    return out

def stats(rows):
    p = np.array([r[0] for r in rows]); eq = np.cumsum(p)
    dd = (np.maximum.accumulate(eq)-eq).max()
    gl=-p[p<0].sum(); gp=p[p>0].sum(); pf=gp/gl if gl>0 else 0
    yr = {y: np.array([r[0] for r in rows if r[1]==y]).sum() for y in ("2023","2024","2025","2026")}
    return p.sum(), dd, pf, (p.sum()/dd if dd>0 else 0), all(v>0 for v in yr.values()), yr

print("=== 1. Stop-multiple PLATEAU sweep (const-risk $15/trade, spread 0.20) ===")
print(f"{'sf':>5} {'net$':>8} {'maxDD$':>8} {'PF':>5} {'ret/DD':>7} {'allYrPos':>8}")
for sf in (0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5):
    net, dd, pf, rdd, allpos, yr = stats(run(sf))
    print(f"{sf:>5.1f} {net:>+8,.0f} {dd:>8,.0f} {pf:>5.2f} {rdd:>7.2f} {'PASS' if allpos else 'FAIL':>8}")

print("\n=== 2. Slippage stress (sf=0.9, const-risk $15/trade) ===")
print(f"{'spread':>7} {'net$':>8} {'maxDD$':>8} {'PF':>5} {'ret/DD':>7} {'allYrPos':>8}")
for sp in (0.20, 0.30, 0.40, 0.50):
    net, dd, pf, rdd, allpos, yr = stats(run(0.9, spread=sp))
    print(f"{sp:>7.2f} {net:>+8,.0f} {dd:>8,.0f} {pf:>5.2f} {rdd:>7.2f} {'PASS' if allpos else 'FAIL':>8}")

print("\n=== 3. Lot-size sanity (sf=0.9, $15/trade, max_lot=1.0) ===")
rows, lots, skipped = run(0.9, return_lots=True)
print(f"  lots: min={lots.min():.3f} p50={np.percentile(lots,50):.3f} "
      f"p95={np.percentile(lots,95):.3f} max={lots.max():.3f}")
print(f"  % trades at max_lot cap (1.0): {100*(lots>=0.999).mean():.1f}%")
print(f"  -> if cap% is high, sizing leans on the cap (hidden risk). Want low.")
# stop-inside-spread check: stop_dist < 2*half would be unreliable
print("\n  min-stop guard (skip trades whose 0.9*ov stop < 1.0pt, ~5x spread):")
net, dd, pf, rdd, allpos, yr = stats(run(0.9, min_stop_pt=1.0))
print(f"    net=${net:+,.0f} maxDD=${dd:,.0f} ret/DD={rdd:.2f} allYrPos={'PASS' if allpos else 'FAIL'}  {yr}")
