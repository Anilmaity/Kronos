"""
SNAP-ICT-MAKER-RP — risk-parity refinement of snap_ict_maker.

Same edge (Daily-ICT-gated maker mean-reversion fade in the 03-09 UTC quiet window), with
two evidence-backed changes from the 2026-06-28 loss-tail research (s5_volaware_*.py):

  1. TIGHTER STOP  1.5*ov -> 0.9*ov.
     MAE analysis showed the 1.5*ov stop is far wider than winners need: 97.7% of winners
     drew down <1.5*ov but 93% drew down <1.0*ov, and the profitable big overshoots draw
     down LESS in ov-units (p90 0.77 vs 0.86). Tightening to 0.9*ov raised walk-forward P&L
     +$2,757 -> +$3,262 (+18%) at fixed lot AND lifted the weak 2025 OOS year +$186 -> +$890.
     Plateau is wide: every sf in 0.6..1.2 stays positive every year (s5_volaware_robust.py).

  2. CONSTANT-$-RISK SIZING (risk parity) instead of a fixed 0.10 lot.
     The $ tail is intrinsic to a proportional stop on huge overshoots (a 30pt overshoot at
     0.9*ov is ~$270 risk at fixed lot). Sizing each trade to risk a constant $ flattens the
     tail completely: every loss == RISK_USD, 0 trades worse than -$80, max single loss == the
     budget. return/drawdown roughly doubles vs the fixed-lot base (1.93 -> ~4.2). This is the
     right shape for a drawdown-limited FundingPips challenge: bounded per-trade loss, and you
     dial RISK_USD to the target instead of over-sizing.

  Also: MIN_STOP_PT guard skips trades whose 0.9*ov stop would sit < 1.0pt (~5x spread),
  where fills are unreliable; it barely changes results (load-bearing check passed).

MAKER-DEPENDENT (unchanged, and re-confirmed at the new params):
  maker +$1,604 PASS-all-years  vs  taker -$3,730 FAIL (blows drawdown).
  Requires an account that posts limits and earns/saves the spread (raw/ECN). On a spread-only
  taker account this LOSES. The gating question (is the live account maker-capable?) is unchanged.

Run: .venv/Scripts/python.exe bot/snap_ict_maker_rp.py
"""
import os, sys, numpy as np
try:
    from . import snap_ict_maker as M          # imported as package module
except ImportError:                            # run directly as a script
    sys.path.insert(0, os.path.dirname(__file__))
    import snap_ict_maker as M

# ---- refined parameters ----
STOP_F   = 0.9      # was 1.5 (M.STOP_F); middle of the 0.6..1.2 robustness plateau
RISK_USD = 15.0     # constant $ risked per trade (dial to account/target)
PER_PT_PER_LOT = 100.0   # $ per point per 1.0 lot (0.10 lot == $10/pt)
MAX_LOT  = 1.0
MIN_STOP_PT = 1.0   # skip trades whose stop would be < this (unreliable near spread)

def backtest_rp(t, o, c, h, l, bias=None, spread=M.SPREAD,
                stop_f=STOP_F, risk_usd=RISK_USD, max_lot=MAX_LOT, min_stop_pt=MIN_STOP_PT):
    """Risk-parity maker fade. Returns list of (pnl_usd, lot, time)."""
    n = len(c); half = spread/2
    hour, mv, sd, rv, thr = M.indicators(t, c, h, l)
    if bias is None: bias = M.daily_ict_bias(t, c, h, l)
    out = []; i = M.W + 1
    while i < n - 2:
        ok = (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i] > 0 and M.SESSION(hour[i])
              and np.isfinite(rv[i]) and np.isfinite(thr[i]) and rv[i] < thr[i] and abs(mv[i]) >= M.K*sd[i])
        if not ok: i += 1; continue
        up = mv[i] > 0; side = -1 if up else 1; ov = abs(mv[i])
        if bias[i] == 0 or np.sign(side) != bias[i]: i += 1; continue
        stop_dist = stop_f*ov
        if stop_dist < min_stop_pt: i += 1; continue
        L = c[i] + (M.OFFSET*sd[i] if up else -M.OFFSET*sd[i]); fj = None
        for j in range(i+1, min(i+1+M.FILL_WIN, n)):
            if up and h[j] >= L: fj = j; break
            if (not up) and l[j] <= L: fj = j; break
        if fj is None: i += 1; continue
        entry = L
        target = entry - M.TARGET_F*ov if up else entry + M.TARGET_F*ov
        stop   = entry + stop_dist     if up else entry - stop_dist
        lot = min(risk_usd/(stop_dist*PER_PT_PER_LOT), max_lot)
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
        out.append((pnl_pt*PER_PT_PER_LOT*lot, lot, t[i])); i = j + 1   # full timestamp
    return out

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "..", "reports", "xau_m5_3y.csv")
    t, o, c, h, l = M.load(path); tr = backtest_rp(t, o, c, h, l)
    p = np.array([x for x, _, _ in tr]); yrs = np.array([tt[:4] for _, _, tt in tr])
    eq = np.cumsum(p); dd = (np.maximum.accumulate(eq)-eq).max()
    print(f"SNAP-ICT-MAKER-RP  (stop {STOP_F}*ov, const-risk ${RISK_USD}/trade, spread {M.SPREAD}):")
    for y in ("2023", "2024", "2025", "2026"):
        q = p[yrs == y]
        if not len(q): continue
        gl = -q[q<0].sum(); gp = q[q>0].sum(); pf = gp/gl if gl>0 else float('inf')
        tag = "" if y in ("2023","2024") else " (OOS)"
        print(f"  {y}{tag}: n={len(q):4d}  WR={100*(q>0).mean():3.0f}%  PnL=${q.sum():>+7,.0f}  PF={pf:.2f}")
    gl=-p[p<0].sum(); gp=p[p>0].sum()
    print(f"  ALL: n={len(p)}  PnL=${p.sum():+,.0f}  PF={gp/gl:.2f}  maxDD=${dd:,.0f}  "
          f"return/DD={p.sum()/dd:.2f}  worstTrade=${p.min():+.0f}")
