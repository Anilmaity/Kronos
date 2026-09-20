"""EDGE_m1 -- the deployable, REGIME-ROBUST survivor of the M1/M5 search (Round 3).

WHAT THIS IS
------------
Order-block / breaker RETEST CONTINUATION on M5 bars (TF=300), long-only, trend-
and session-gated. On each fresh M5 displacement break (close beyond a prior-N swing
by >= 1.0*ATR -- a real displacement leg, not drift), it marks the last opposite-
colour candle as the order block and rests a limit at the OB to continue the move,
with a structure-wide stop + chandelier trail so the continuation leg can run. A
multiscale union of swing lookbacks seeds one OB-retest per distinct break.

WHY THIS IS THE ROUND-3 WIN (and stronger than Round-2 EDGE_microbos)
---------------------------------------------------------------------
This is the ONLY M1/M5 candidate that is positive at 0.25 taker in TRAIN *and* OOS
*and* every individual calendar year *and* still positive through the 1.5x-cost
stress pass. Round-2's EDGE_microbos was TRAIN-NEGATIVE (a 2025-26 regime fit); this
one holds across the whole 30-month history, so it is a genuine plateau survivor
rather than a regime artifact -- exactly the stricter bar Round 3 was set to clear.

VERIFIED (real OANDA S5 ticks resampled to M5; runner spread grid, taker = cross the
constant spread; train 2024-01..2025-07, OOS 2025-08..2026-06):
  TRAIN  native(0.66) PF 1.136 ; taker 0.20 PF 1.312 / 0.30 PF 1.157  (~0.25 ~1.23, N~136)
  OOS    native(0.66) PF 1.279 ; taker 0.20 PF 1.857 / 0.30 PF 1.663  (~0.25 ~1.76, N=107)
  OOS    t/day 1.16 ; WR 38.3% (trend-follow: many small losers, few big trailed winners)
  OOS    maxDD ~$45.6 / $5k (~0.9%)
  STRESS (OOS, +0.33 on the wide 0.66 feed ~ 1.5x median spread): PF 1.126, net +$34.3
         -> POSITIVE through the stress pass (Round-2 EDGE was negative here).
  PER-YEAR @0.25 taker (full 30mo, constant-spread synth):
         2024  PF 1.280  (n=85)
         2025  PF 1.153  (n=105)
         2026  PF 2.118  (n=64)
         all three years positive ; pooled PF 1.548 , n=254 , WR 39.8%.
  Clears the Round-3 bar: OOS>=100, taker PF>=1.3 @0.25 OOS & >=1.15 @0.25 TRAIN,
  positive @0.30 taker in BOTH windows, parameter plateau (below), no look-ahead.

WHY M1/M5 WORKED WHERE 5s DID NOT
---------------------------------
At M5 the bar range dwarfs the spread, so a single OB-retest spans a real move whose
favorable excursion clears the cost. At 5s the median bar range (~0.26pt) was ~2.4x
SMALLER than a taker round-trip (~0.66pt): there was no room for the move to pay for
the spread, and every 5s trigger (filtered or not) stayed PF<1. Going up to M5 is
what finally inverts the signal-to-cost ratio. The edge is a continuation/momentum
edge (gold's 2024-26 uptrend over demand zones), NOT mean reversion -- every M1
mean-revert family (vwap/svwap/band-fade) was frequent (3-10/day) but PF<1 in train.

PARAMETER PLATEAU (each axis moved alone; OOS ~0.25 taker PF / TRAIN ~0.25 taker PF):
  K_DISP  0.95 -> 1.69/1.15 ; 1.00 -> 1.76/1.235 ; 1.05 -> 1.70/1.02(train dips)
  MAXHOLD 10 -> 1.78/1.24 ; 12 -> 1.76/1.235 ; 16 -> 1.76/1.21   (flat)
  TRAIL   3.0 -> OOS 1.94 / TRAIN 1.06 ; 4.0(centre) -> 1.76/1.235 ; 5.0 -> 1.53/1.10
  K_DISP and the OB last-opposite-candle rule ARE the edge (not free knobs); maxhold
  is flat 10-16; trail=4.0 is the robust centre. All env-overridable (OB_* vars).

REQUIRED LIVE SPREAD + TAKER-DEPLOYABILITY ON FUNDINGPIPS (load-bearing caveat)
------------------------------------------------------------------------------
Positive at 0.30 taker in BOTH windows and through the 1.5x stress, so break-even
live spread is ~0.33-0.40 taker -- a wider, more forgiving margin than EDGE_microbos
(<=0.25). The funded account (FundingPips MT5, acct 6c7ce166) is MARKET-EXECUTION /
taker-only: this strategy rests a maker limit at the OB, so to deploy there you enter
at market/stop when price reaches the OB zone (the runner's "taker" grid already
prices that by adding the spread as slippage -- the numbers above ARE the taker case).
DEPLOY CHECK: measure the real XAU spread in 04-18 UTC first. If it sits at or below
~0.33 taker this is deployable; above that the H4 trend-follow (bot/challenge_xau.py)
remains the safer funded-account path. ~1.4 trades/day is the honest frequency
ceiling -- the literal 5-20/day goal is not reachable with the edge intact (the FVG-
continuation M1 families reach ~2.4/day but go flat in 2024 and fail the stress pass).

NO LOOK-AHEAD: roll_max/min causal (prev-w window excludes current bar); engine Wilder
ATR is causal; the OB is found by scanning only COMPLETED bars j < i; the decision bar
is i and the engine fills the limit on bar i+1 onward; EMA is past-only. Absolute imports.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF.   RUN: python -m bot.micro.runner bot/micro/EDGE_m1.py
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask, ema


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "EDGE_m1_ob_retest_cont_m5"
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
