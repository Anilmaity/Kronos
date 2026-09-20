"""
s5_volaware_sizing.py — Combine tighter stop + constant-$-risk sizing; measure the REAL
tail (loss percentiles + simulated equity max drawdown), not the noisy single-worst trade.

Why sizing: the $ tail is intrinsic to trading huge overshoots with a proportional stop
(a 30pt overshoot at 1.0*ov is still ~$300 risk at fixed lot). Constant-risk sizing scales
the lot DOWN on big overshoots so every trade risks ~the same $ -> flat tail, the right
fix for a drawdown-limited FundingPips challenge.

Compares, on the same trade engine:
  fixed lot 0.10 (base stop 1.5*ov)        <- current deployed model
  fixed lot 0.10 (tighter stop 0.9*ov)     <- P&L/robustness winner from s5_volaware_stop
  const-risk  (tighter stop 0.9*ov)        <- tail fix
"""
import os, numpy as np
import bot.snap_ict_maker as M

path = os.path.join(os.path.dirname(__file__), "reports", "xau_m5_3y.csv")
t, o, c, h, l = M.load(path)
bias = M.daily_ict_bias(t, c, h, l)
n = len(c)
hour, mv, sd, rv, thr = M.indicators(t, c, h, l)

PER_PT_PER_LOT = 100.0  # $ per point per 1.0 lot (0.10 lot = $10/pt, matches base)

def run(sf, sizing="fixed", fixed_lot=0.10, risk_usd=10.0, max_lot=1.0):
    """Returns list of (pnl_usd, ov, year). sf=stop multiple of ov."""
    out = []
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
        stop   = entry + sf*ov         if up else entry - sf*ov
        stop_dist = sf*ov  # points of risk
        if sizing == "fixed":
            lot = fixed_lot
        else:  # const risk: lot s.t. stop_dist * PER_PT_PER_LOT * lot = risk_usd
            lot = risk_usd / (stop_dist * PER_PT_PER_LOT) if stop_dist > 0 else 0
            lot = min(lot, max_lot)
        ex = None; mk = False
        for j in range(fj+1, min(fj+1+M.TIME, n)):
            if up:
                if h[j] >= stop: ex = stop; break
                if l[j] <= target: ex = target; mk = True; break
            else:
                if l[j] <= stop: ex = stop; break
                if h[j] >= target: ex = target; mk = True; break
        if ex is None: ex = c[min(fj+M.TIME, n-1)]
        pnl_pt = (ex-entry)*side + M.HALF + (M.HALF if mk else -M.HALF)
        out.append((pnl_pt * PER_PT_PER_LOT * lot, ov, t[i][:4]))
        i = j + 1
    return out

def maxdd(pnl):
    eq = np.cumsum(pnl); peak = np.maximum.accumulate(eq); return (peak - eq).max()

def report(name, rows):
    pnl = np.array([r[0] for r in rows])
    tot = pnl.sum(); wr = 100*(pnl>0).mean()
    gl = -pnl[pnl<0].sum(); gp = pnl[pnl>0].sum(); pf = gp/gl if gl>0 else 0
    dd = maxdd(pnl)
    print(f"\n{name}")
    print(f"  n={len(pnl)}  net=${tot:+,.0f}  WR={wr:.0f}%  PF={pf:.2f}  maxDD=${dd:,.0f}  "
          f"return/DD={tot/dd if dd>0 else 0:.2f}")
    yr = {y: np.array([r[0] for r in rows if r[2]==y]).sum() for y in ("2023","2024","2025","2026")}
    print("  by year: " + "  ".join(f"{y}:${v:+,.0f}" for y,v in yr.items()))
    print(f"  loss tail: p1=${np.percentile(pnl,1):+.0f} p5=${np.percentile(pnl,5):+.0f} "
          f"worst=${pnl.min():+.0f}  #trades<-$80: {(pnl<-80).sum()}")

print("=== Tighter stop + constant-risk sizing ===")
report("A) base: fixed 0.10 lot, stop 1.5*ov  [CURRENT]", run(1.5, "fixed"))
report("B) fixed 0.10 lot, stop 0.9*ov  [P&L winner]",    run(0.9, "fixed"))
report("C) const-risk $10/trade, stop 0.9*ov  [tail fix]", run(0.9, "risk", risk_usd=10.0))
report("D) const-risk $15/trade, stop 0.9*ov",             run(0.9, "risk", risk_usd=15.0))
report("E) const-risk $20/trade, stop 0.9*ov",             run(0.9, "risk", risk_usd=20.0))
