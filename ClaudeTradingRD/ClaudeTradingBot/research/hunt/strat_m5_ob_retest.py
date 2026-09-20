"""strat_m5_ob_retest -- M5 order-block RETEST CONTINUATION, frequency-pushed.

ASSIGNMENT
----------
Implement the OB-retest continuation family on M5 (TF=300) and try to push it to
3-6 trades/day by adding SESSIONS / kill-zone windows and more order-block
context instances, WITHOUT loosening the displacement/retest that is the edge.

WHAT THIS IS (unchanged edge mechanics from the proven EDGE_m1 survivor)
------------------------------------------------------------------------
Long-only (gold's 2024-26 uptrend; shorts proven to lose in this family). On each
fresh M5 displacement break -- close beyond a prior-N swing extreme by >= K*ATR, a
real displacement leg not drift -- mark the last opposite-colour candle as the
order block and rest a limit at the OB to continue the move, with a structure-wide
stop + chandelier trail so the continuation leg can run. A multiscale union of swing
lookbacks seeds one OB-retest per distinct break; slow-EMA trend bias gates side.

FREQUENCY LEVERS APPLIED (the sanctioned axes -- MORE sessions / MORE OB contexts):
  * SESSION_HOURS widened from London+NY (4-18) to the full 24h clock, so genuine
    OB-retest legs in the Asian / late-US windows are also taken.
  * LOOKBACKS gains one shorter structural swing (3) on top of the 4..40 union, so a
    second, more-local displacement break on the same day can seed a distinct OB.
  * MAXHOLD tightened 12->10 M5 bars to clear occupancy a little faster.
  These add DISTINCT continuation legs; they do NOT touch K_DISP, the OB
  last-opposite-candle rule, the trend/vol gates, or the trail -- those ARE the edge.

HONEST RESULT (real OANDA S5 -> M5; runner spread grid; train 2024-01..2025-07,
OOS 2025-08..2026-06). Judge on the 0.25 TAKER interpolation (funded acct is taker):
  OOS   0.20 taker PF 1.645 / 0.30 taker PF 1.502  -> ~0.25 taker PF ~1.57, N=190
  OOS   trades/day 1.35 ; WR ~41% (trend-follow: many small losers, few trailed wins)
  OOS   maxDD ~$38.7 native / ~$5k account
  TRAIN 0.20 taker PF 1.218 / 0.30 taker PF 1.035  -> positive @0.30 taker BOTH windows
  STRESS (OOS, +0.33 on the wide feed ~1.5x median spread): PF 1.115, net +$48.8 -> positive.

  ==> Clears the acceptance bar (OOS N>=100, OOS 0.25-taker PF>=1.3, positive @0.30
      taker in both windows, stress-positive) BUT falls far short of the 3-6/day
      frequency target: the honest ceiling for a real OB-retest edge is ~1.35/day.
      Probes confirmed the repo's known wall: every push either lands on NEW days
      (per-day density stays ~1.2-1.3, only breadth grows) or, when local/short swings
      are added (LB 2), train 0.30-taker collapses to 0.947 -- i.e. noise. Single-
      position occupancy is NOT the bind (avg hold ~13 min); distinct displacement
      legs on XAU simply print ~1.3/day. Depths (0.0/0.33/0.66) add ZERO trades
      because the shallowest retest always fills first and blocks the rest.

NO LOOK-AHEAD: roll_max/roll_min are causal (prev-w window EXCLUDES the current bar,
NaN warmup -> np.isfinite-gated); engine ATR is causal Wilder; the OB is found by
scanning only COMPLETED bars k<i; the decision bar is i and the engine fills the
limit on bar i+1 onward; ema() is past-only. Absolute imports; TF drives resample.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF=300.
RUN: .venv/Scripts/python.exe -m bot.micro.runner research/hunt/strat_m5_ob_retest.py
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask, ema


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "strat_m5_ob_retest_freqpush"
TF = _P("OB_TF", 300, int)   # execution timeframe seconds (60=M1, 300=M5)

TRAIL = _P("OB_TRAIL", 4.0)            # chandelier trail-only exit (tp=inf) when >0
SIM = dict(maxhold=_P("OB_MAXHOLD", 10, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("OB_COOLDOWN", 0, int), trail_pts=TRAIL)

# frequency lever 1: extra shorter structural swing (3) on top of the 4..40 union
LOOKBACKS = tuple(int(x) for x in
                  os.environ.get("OB_LBS", "3,4,6,8,10,12,15,19,24,30,40").split(","))
K_DISP   = _P("OB_K", 1.00)            # displacement floor: close beyond extreme >= K*ATR (EDGE)
OB_SCAN  = _P("OB_SCAN", 2, int)       # textbook OB: last opposite candle within this many bars
BUF_ATR  = _P("OB_BUF", 0.25)          # stop buffer beyond OB far edge, in ATR
RR       = _P("OB_RR", 2.0)            # reward:risk (fixed-target mode; unused when TRAIL>0)
DEPTHS   = tuple(float(x) for x in os.environ.get("OB_DEPTHS", "0.0,0.5").split(",") if x != "")
TTL      = _P("OB_TTL", 36, int)       # retest limit live bars (~3h on M5)
ATR_LO   = _P("OB_ATRLO", 0.40)
ATR_HI   = _P("OB_ATRHI", 30.0)
BIAS_EMA = _P("OB_BIAS", 100, int)     # slow EMA trend bias (M5 bars)
SL_MIN   = _P("OB_SLMIN", 1.0)         # floor on stop distance (pts)
SL_MAX   = _P("OB_SLMAX", 16.0)        # cap on stop distance (pts) -> reject huge OBs
SIDE     = _P("OB_SIDE", 1, int)       # 0=both, 1=long-only, -1=short-only (survivor=long)
# frequency lever 2: full 24h clock instead of just London+NY (4-18)
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("OB_HOURS",
                                     "0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,"
                                     "16,17,18,19,20,21,22,23").split(","))


def generate(b: Bars) -> Signals:
    n = b.n
    c = b.mid
    o = (b.bo + b.ao) * 0.5
    h = (b.bh + b.ah) * 0.5
    l = (b.bl + b.al) * 0.5
    A = atr(b, 14)
    Eb = ema(c, BIAS_EMA)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)
    bias_up = c > Eb
    bias_dn = c < Eb

    thr = K_DISP * A
    bear = c < o
    bull = c > o

    fu = np.zeros(n, bool); fd = np.zeros(n, bool)
    for L in LOOKBACKS:
        rmax = roll_max(h, L); rmin = roll_min(l, L)   # causal: exclude current bar
        bu = np.isfinite(rmax) & np.isfinite(A) & (c - rmax >= thr) & sess & volok & bias_up
        bd = np.isfinite(rmin) & np.isfinite(A) & (rmin - c >= thr) & sess & volok & bias_dn
        e_u = bu.copy(); e_u[1:] &= ~bu[:-1]   # only the first bar of a fresh break
        e_d = bd.copy(); e_d[1:] &= ~bd[:-1]
        fu |= e_u; fd |= e_d
    if SIDE > 0:
        fd[:] = False
    elif SIDE < 0:
        fu[:] = False

    sig_i = []; sig_side = []; sig_level = []; sig_sl = []; sig_tp = []

    def emit(i, sd, ob_hi, ob_lo):
        for dpth in DEPTHS:
            if sd > 0:
                entry = ob_hi - dpth * (ob_hi - ob_lo)
                sl = ob_lo - BUF_ATR * A[i]
                sl_pts = entry - sl
                if entry >= c[i]:      # retest must be BELOW current price (causal, no chase)
                    continue
            else:
                entry = ob_lo + dpth * (ob_hi - ob_lo)
                sl = ob_hi + BUF_ATR * A[i]
                sl_pts = sl - entry
                if entry <= c[i]:
                    continue
            if not (SL_MIN <= sl_pts <= SL_MAX):
                continue
            tp_pts = (np.inf if TRAIL > 0 else RR * sl_pts)
            sig_i.append(int(i)); sig_side.append(sd); sig_level.append(entry)
            sig_sl.append(sl_pts); sig_tp.append(tp_pts)

    for i in np.where(fu)[0]:
        j = -1
        for k in range(i - 1, max(0, i - OB_SCAN) - 1, -1):   # scan COMPLETED bars only
            if bear[k]:
                j = k; break
        if j >= 0:
            emit(i, 1, h[j], l[j])

    for i in np.where(fd)[0]:
        j = -1
        for k in range(i - 1, max(0, i - OB_SCAN) - 1, -1):
            if bull[k]:
                j = k; break
        if j >= 0:
            emit(i, -1, h[j], l[j])

    if not sig_i:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array(sig_i, np.int64)
    side = np.array(sig_side, np.int64)
    level = np.array(sig_level, np.float64)
    sl_pts = np.array(sig_sl, np.float64)
    tp_pts = np.array(sig_tp, np.float64)
    ord_ = np.argsort(i, kind="stable")
    i, side, level, sl_pts, tp_pts = i[ord_], side[ord_], level[ord_], sl_pts[ord_], tp_pts[ord_]
    m = len(i)
    return Signals(i=i, side=side, kind=np.ones(m, int), level=level,
                   sl_pts=sl_pts, tp_pts=tp_pts, ttl=np.full(m, TTL, np.int64))
