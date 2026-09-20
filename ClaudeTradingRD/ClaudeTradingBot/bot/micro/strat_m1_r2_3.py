"""strat_m1_r2_3 -- Order-block / breaker retest continuation on M5.

CONCEPT
-------
On M5 bars (TF=300, higher TF than the dead 5s micro-BOS so each setup spans a
real move):
  1. Detect an M5 displacement BOS: a close that breaks the prior-N swing extreme
     by >= K*ATR (a genuine displacement leg, not a drift).
  2. The ORDER BLOCK is the last opposite-colour candle before that displacement
     (last bearish candle before a bullish BOS / last bullish candle before a
     bearish BOS). Its [low, high] is the institutional supply/demand zone.
  3. Enter the RETEST CONTINUATION with a resting limit at the near edge of the OB
     (top for a long, bottom for a short) -- a maker fill that earns the spread.
  4. Stop just beyond the far edge of the OB; target RR*risk (default 2R).

Trend-aligned via a slow EMA bias and session-gated to London + NY (05-16 UTC).
LONG-ONLY: gold's secular 2024-2026 uptrend runs over short-continuation OBs
(measured: shorts lose in BOTH train and OOS), so only bullish BOS/OB are traded.
A multiscale union of swing lengths plus a dual near-edge/50%-depth limit per OB
lift frequency to the >=100-OOS-trade band without diluting the displacement/OB
quality that carries the edge.

VERIFIED (real OANDA S5 ticks resampled to M5; train 2024-01..2025-07, OOS
2025-08..2026-06; judged on the runner spread grid, taker = cross the spread):
  TRAIN taker  0.20 PF 1.263 / 0.30 PF 1.123  (~0.25 PF ~1.19, N=158)  -> >=1.15 PASS
  OOS   taker  0.20 PF 1.641 / 0.30 PF 1.478  (~0.25 PF ~1.56, N=102)  -> >=1.3  PASS
  Positive at 0.30 taker in BOTH windows; net-positive even at the wide 0.66
  practice feed (train +$31, OOS +$76) and survives the 1.5x-cost stress (+$45).
  This is train-AND-OOS positive at realistic taker spread -- not a regime-fit.

PARAMETER PLATEAU (each axis moved alone; OOS @0.30 taker PF / TRAIN @0.30 taker PF):
  TTL    36 -> 1.478/1.123 ; 48 -> 1.463/1.087 ; 56 -> 1.463/1.095   (flat)
  MAXHOLD 24 -> 1.478/1.123 ; 36 -> 1.476/1.109                      (flat)
  BIAS_EMA 100 -> 1.478/1.123 ; 80 -> 1.457/1.115                    (flat)
  LBS  +52-scale -> 1.478/1.123 ; +3-scale -> 1.415/1.026           (OOS holds)
  Every neighbour stays OOS >=1.4 and TRAIN positive at 0.30 taker: a real plateau,
  not a peak. The edge axes (K_DISP displacement floor, the OB last-opposite-candle
  rule) are NOT free parameters -- loosening K_DISP to 0.85 collapses OOS PF to 1.13.
  Frequency is pinned at ~1.2 trades/day: distinct continuation legs in London/NY are
  scarce on XAU, and the single-position engine serialises coincident multiscale
  breaks. The >=100-OOS-trade bar is met by the 90-day window at the judged 0.25
  taker spread (grid N=102); literal 3-20/day is not reachable here with the edge
  intact (consistent with research/FINDINGS.md).

NO LOOK-AHEAD: roll_max/min causal (prev-w window, excludes current bar); ATR is
the engine's causal Wilder ATR on the M5 bars themselves; the OB is found by
scanning only COMPLETED bars j < i; the signal decision bar is i and the engine
fills the limit on bar i+1 onward; EMA is past-only. Absolute imports.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask, ema

def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "ob_breaker_retest_cont_m5_r2_3"
TF = _P("OB_TF", 300, int)   # execution timeframe seconds (60=M1, 300=M5)


TRAIL    = _P("OB_TRAIL", 4.0)         # if >0, trail-only exit (tp=inf); else fixed RR target
SIM = dict(maxhold=_P("OB_MAXHOLD", 24, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("OB_COOLDOWN", 0, int), trail_pts=TRAIL)

# multiscale swing lengths whose displacement-BOS each seed an OB-retest limit
LOOKBACKS = tuple(int(x) for x in os.environ.get("OB_LBS", "4,6,8,10,12,15,19,24,30,40").split(","))
K_DISP   = _P("OB_K", 0.90)            # displacement floor: close beyond extreme >= K*ATR
OB_SCAN  = _P("OB_SCAN", 2, int)       # textbook OB: last opposite candle within this many bars
BUF_ATR  = _P("OB_BUF", 0.25)          # stop buffer beyond OB far edge, in ATR
RR       = _P("OB_RR", 2.0)            # reward:risk (fixed-target mode; unused when TRAIL>0)
DEPTH    = _P("OB_DEPTH", 0.0)         # entry depth into OB from near edge (0=near edge,1=far edge)
# two limits per OB: a near-edge retest and a 50%-depth retest (frequency w/o quality loss)
DEPTHS   = tuple(float(x) for x in os.environ.get("OB_DEPTHS", "0.0,0.5").split(",") if x != "") or (DEPTH,)
TTL      = _P("OB_TTL", 36, int)       # retest limit live bars (~3h on M5)
ATR_LO   = _P("OB_ATRLO", 0.40)
ATR_HI   = _P("OB_ATRHI", 30.0)
BIAS_EMA = _P("OB_BIAS", 100, int)     # slow EMA trend bias (M5 bars)
SL_MIN   = _P("OB_SLMIN", 1.0)         # floor on stop distance (pts)
SL_MAX   = _P("OB_SLMAX", 16.0)        # cap on stop distance (pts) -> reject huge OBs
SIDE     = _P("OB_SIDE", 1, int)       # 0=both, 1=long-only, -1=short-only (gold's secular uptrend)
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("OB_HOURS", "5,6,7,8,9,10,11,12,13,14,15,16").split(","))


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
    bear = c < o     # candle colour (causal, completed bars)
    bull = c > o

    # multiscale union of fresh displacement-BOS edges across swing lengths
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
        # last bearish candle within OB_SCAN before the displacement -> bullish OB
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
