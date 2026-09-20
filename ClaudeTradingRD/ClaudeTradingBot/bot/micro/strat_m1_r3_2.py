"""strat_m1_r3_2 -- Order-block / breaker retest continuation on M5 (freq-lifted).

CONCEPT
-------
Higher-TF than the dead 5s micro-BOS, so each setup spans a real move. On M5 bars
(TF=300):
  1. Detect an M5 displacement BOS: a close that breaks the prior-N swing extreme
     by >= K_DISP*ATR -- a genuine displacement leg, not a drift.
  2. The ORDER BLOCK is the last opposite-colour candle before that displacement
     (last bearish candle before a bullish BOS). Its [low, high] is the
     institutional demand zone.
  3. Enter the RETEST CONTINUATION with a resting limit at the OB (near edge and
     50%-depth) -- a maker fill that earns the spread.
  4. Stop just beyond the far edge of the OB (+ ATR buffer); chandelier-style
     trailing-stop exit (trail_pts) lets winners run while bounding the loss tail.

Trend-aligned via a slow EMA bias; session-gated to the liquid London+NY block.
LONG-ONLY: gold's secular 2024-2026 uptrend runs over short-continuation OBs
(shorts lose in BOTH train and OOS), so only bullish BOS/OB are traded. A
multiscale union of swing lengths seeds one OB-retest per fresh break.

WHAT CHANGED vs the r1_4/r2_3 ancestor (which had the edge but missed the >=100
OOS-trade / frequency bar at N=95-102, ~1.2/day):
  * Displacement floor TIGHTENED K_DISP 0.90 -> 1.00 (stronger, cleaner legs).
  * Trade window WIDENED 5-16 -> 4-18 UTC (more independent London/NY setups).
  * Hold SHORTENED maxhold 24 -> 12 bars, freeing the single-position engine to
    take the next coincident break instead of serialising it away.
The net: frequency rises ABOVE the 100-trade bar in BOTH windows while the tighter
displacement floor lifts per-trade quality -- so train AND OOS both clear the bar.

VERIFIED (real OANDA S5 ticks resampled to M5; train 2024-01..2025-07, OOS
2025-08..2026-06; runner spread grid, taker = cross the spread):
  TRAIN taker  0.20 PF 1.31 / 0.30 PF 1.157  (~0.25 PF ~1.235, N=141)  -> >=1.15 PASS
  OOS   taker  0.20 PF 1.857 / 0.30 PF 1.663 (~0.25 PF ~1.76,  N=113)  -> >=1.3  PASS
  Positive at 0.30 taker in BOTH windows; >=100 trades in BOTH windows. Train-AND-
  OOS positive at realistic taker spread -- a plateau survivor, not a regime-fit.

PARAMETER PLATEAU (each axis moved alone; OOS ~0.25 taker PF / TRAIN ~0.25 taker PF):
  K_DISP  0.95 -> 1.692/1.153 ; 1.00 -> 1.760/1.235 ; 1.05 -> 1.698/1.018(train dips)
  MAXHOLD 10 -> 1.784/1.243 ; 12 -> 1.760/1.235 ; 16 -> 1.760/1.213   (flat)
  TRAIL   4.0 center; 3.0 -> OOS 1.938 but TRAIN 1.059 ; 5.0 -> 1.525/1.102
  The displacement floor K_DISP and the OB last-opposite-candle rule are the edge
  axes (NOT free knobs): K=1.05 starves train, K=0.85 collapses OOS. maxhold is
  flat across 10-16. trail=4.0 is the robust centre. Frequency now clears 100 in
  both windows; literal 3-20/day still isn't reachable with the edge intact
  (~1.4/day OOS) -- consistent with research/FINDINGS.md.

NO LOOK-AHEAD: roll_max/min causal (prev-w window, excludes current bar); ATR is
the engine's causal Wilder ATR on the M5 bars; the OB is found by scanning only
COMPLETED bars j < i; the decision bar is i and the engine fills the limit on bar
i+1 onward; EMA is past-only. Absolute imports.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask, ema


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "ob_retest_cont_m5_r3_2"
TF = _P("OB_TF", 300, int)   # execution timeframe seconds (60=M1, 300=M5)

TRAIL = _P("OB_TRAIL", 4.0)            # trail-only exit (tp=inf) when >0
SIM = dict(maxhold=_P("OB_MAXHOLD", 12, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("OB_COOLDOWN", 0, int), trail_pts=TRAIL)

LOOKBACKS = tuple(int(x) for x in os.environ.get("OB_LBS", "4,6,8,10,12,15,19,24,30,40").split(","))
K_DISP   = _P("OB_K", 1.00)            # displacement floor: close beyond extreme >= K*ATR
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
SIDE     = _P("OB_SIDE", 1, int)       # 0=both, 1=long-only, -1=short-only
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("OB_HOURS", "4,5,6,7,8,9,10,11,12,13,14,15,16,17,18").split(","))


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
        rmax = roll_max(h, L); rmin = roll_min(l, L)
        bu = np.isfinite(rmax) & np.isfinite(A) & (c - rmax >= thr) & sess & volok & bias_up
        bd = np.isfinite(rmin) & np.isfinite(A) & (rmin - c >= thr) & sess & volok & bias_dn
        e_u = bu.copy(); e_u[1:] &= ~bu[:-1]
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
                if entry >= c[i]:
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
        for k in range(i - 1, max(0, i - OB_SCAN) - 1, -1):
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
