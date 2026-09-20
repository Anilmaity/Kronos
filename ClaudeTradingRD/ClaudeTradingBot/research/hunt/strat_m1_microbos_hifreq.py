"""strat_m1_microbos_hifreq -- M1 micro-BOS continuation, frequency-expansion attempt.

GOAL: take the project's proven micro-BOS continuation edge (a deep maker retest of a
genuine >=K*ATR displacement break, trend- and session-gated, trailed so the leg runs)
and try to lift it from ~1.5/day toward 5+/day on M1 bars by (a) unioning MANY swing
lookback scales and (b) opening MANY session windows -- WITHOUT re-counting the same
leg (the documented single-position occupancy wall) and WITHOUT loosening the trigger
into noise (the documented PF-collapse of looser K/RETR/hold).

MECHANICS (all on M1 mid bars, TF=60):
  * fresh break: close beyond prior-N M1 high (long) by >= K_DISP * ATR(14).
  * "fresh" = the break condition flips False->True (edge), so a persistent break is
    counted ONCE per scale (occupancy already serialises coincident scales).
  * trend bias: mid vs slow EMA. Long-only by default (gold 2024-26 uptrend; shorts
    lose in the repo's tests).
  * session gate: an explicit UTC hour list -- the frequency lever is WIDENING this.
  * entry: maker LIMIT resting at a deep retest of the displacement
    level = c[i] - RETR * displacement  (so it earns the pullback; judged on taker grid).
  * stop: structure-wide, k*ATR from fill (adaptive), floored/capped.
  * exit: trail-only chandelier (tp=inf, SIM.trail_pts) so the few real legs run.
  * INTRA-LEG RE-ARM (the non-noise frequency mechanism): within one live long leg,
    each fresh higher-high extension that displaces again re-arms one more retest entry
    (>= REARM_GAP bars apart, capped). These are DISTINCT continuation pushes of the
    leg, not re-counts of the opener break.

RESULT (VERDICT: DEAD-END for the taker bar) -- measured via bot.micro.runner, real
OANDA S5 -> M1, train 2024-01..2025-07 / OOS 2025-08..2026-06:
  Default cfg here (~4.0 trades/day, in the 3-6 target band):
    OOS N=970, WR 26.5%, OOS 0.25-taker PF ~0.89 (0.20->0.937, 0.30->0.840),
    TRAIN 0.25-taker PF <1 (0.20->0.803, 0.30->0.669), OOS 1.5x-stress net -$760 (PF 0.63).
  Tighter "quality core" (K=1.8, RETR=0.62, LBS 8,12,18,26, hours 7-15, no re-arm,
    trail 4, maxhold 60) -> only ~1.36 trades/day, OOS 0.25-taker PF ~1.07, but STILL
    TRAIN-taker-negative (0.73/0.63). Best OOS taker found anywhere in the search ~1.07.
  CONCLUSION: on M1 the micro-BOS retest edge lives ENTIRELY in the spread -- maker PF
    ~1.05-1.27 but taker collapses to <=1.07 because the per-trade favorable excursion
    barely exceeds a 0.25pt round-trip (M1 ATR ~2.0pt; the retest move is small). This
    reproduces the repo's documented cost floor: M5>M1>>5s. Every lever tried to lift
    frequency (7 lookback scales, wider 06-16/00-20 sessions, intra-leg re-arm) reached
    3-7 trades/day but NEVER cleared OOS PF>=1.3 @0.25 taker and was TRAIN-taker-negative
    in every config. No config is positive in BOTH windows at 0.30 taker. Frequency was
    reachable; a taker-survivable edge at that frequency was NOT. Left on disk as a
    well-tested negative. The deployable M1/M5 continuation remains bot/micro/EDGE_m1.py.

NO LOOK-AHEAD: roll_max/roll_min exclude the current bar (NaN warmup -> isfinite gate);
engine.atr is Wilder-causal; EMA is past-only; every decision at bar i uses only bars<=i
and the engine fills the limit on bar i+1 onward; the re-arm loop reads mid[i] and the
causal rolling extremes only. Absolute imports.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF=60.
RUN: .venv/Scripts/python.exe -m bot.micro.runner research/hunt/strat_m1_microbos_hifreq.py
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask, ema


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "m1_microbos_hifreq"
TF = _P("MB_TF", 60, int)

# ---- exit / sizing ----
TRAIL   = _P("MB_TRAIL", 5.0)
_RR0    = _P("MB_RR", 0.0)             # read early to decide trail vs fixed-target exit
SIM = dict(maxhold=_P("MB_MAXHOLD", 75, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("MB_COOLDOWN", 0, int), trail_pts=(TRAIL if _RR0 <= 0 else 0.0))

# ---- multiscale opener lookbacks (M1 bars) ----
LOOKBACKS = tuple(int(x) for x in os.environ.get("MB_LBS", "6,10,16,24,36").split(","))
LEG_LB    = _P("MB_LEGLB", 12, int)   # lookback whose legs carry the re-arm rungs

# ---- micro-BOS trigger params ----
K_DISP   = _P("MB_K", 1.30)           # displacement floor >= K_DISP * ATR
RETR     = _P("MB_RETR", 0.50)        # retest depth into the displacement (deep = better fill)
RR       = _P("MB_RR", 0.0)           # >0: fixed target = RR * sl_pts (tp). 0: trail-only.
SL_K     = _P("MB_SLK", 1.30)         # stop distance = SL_K * ATR from fill
SL_MIN   = _P("MB_SLMIN", 1.5)
SL_MAX   = _P("MB_SLMAX", 16.0)
TTL      = _P("MB_TTL", 30, int)      # retest limit live bars (~30 min)
ATR_LO   = _P("MB_ATRLO", 0.25)
ATR_HI   = _P("MB_ATRHI", 30.0)
BIAS_EMA = _P("MB_BIAS", 100, int)    # slow EMA trend bias (M1 bars ~1.6h)
SIDE     = _P("MB_SIDE", 1, int)      # 0=both 1=long-only -1=short-only

# frequency lever: WIDE session gate (London+NY default; env-widen to add windows)
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("MB_HOURS", "6,7,8,9,10,11,12,13,14,15,16").split(","))

# ---- re-arm lever ----
REARM_ON   = _P("MB_REARM", 1, int)
LEG_INVALID = _P("MB_INV", 6.0)       # leg dies if price retraces this many pts off extreme
REARM_GAP  = _P("MB_GAP", 12, int)    # min M1 bars between rungs in one leg
EXT_PTS    = _P("MB_EXT", 0.60)       # new extreme must exceed prior rung by this many pts
MAX_RUNGS  = _P("MB_MR", 12, int)
MIN_DEPTH  = _P("MB_MINDEPTH", 0.40)  # rung limit must sit >= this many pts inside (maker)
RETR_FLOOR = _P("MB_RFLOOR", 0.40)


def _breaks(mid, A, sess, volok, bias_up, bias_dn, lookback):
    rmax = roll_max(mid, lookback)
    rmin = roll_min(mid, lookback)
    disp_up = mid - rmax
    disp_dn = rmin - mid
    thr = K_DISP * A
    bu = np.isfinite(rmax) & np.isfinite(A) & (disp_up >= thr) & sess & volok & bias_up
    bd = np.isfinite(rmin) & np.isfinite(A) & (disp_dn >= thr) & sess & volok & bias_dn
    fu = bu.copy(); fu[1:] &= ~bu[:-1]
    fd = bd.copy(); fd[1:] &= ~bd[:-1]
    return fu, fd, disp_up, disp_dn


def generate(b: Bars) -> Signals:
    n = b.n
    mid = b.mid
    A = atr(b, 14)
    a0 = np.where(np.isfinite(A), A, 0.0)
    Eb = ema(mid, BIAS_EMA)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)
    bias_up = mid > Eb
    bias_dn = mid < Eb

    sig_i = []; sig_side = []; sig_level = []; sig_sl = []; sig_tp = []

    def _sl_pts(i):
        s = SL_K * a0[i]
        return min(max(s, SL_MIN), SL_MAX)

    def emit(i, sd, level):
        sp = _sl_pts(i)
        if sd > 0 and level >= mid[i]:
            return
        if sd < 0 and level <= mid[i]:
            return
        sig_i.append(int(i)); sig_side.append(sd); sig_level.append(level); sig_sl.append(sp)
        sig_tp.append(RR * sp if RR > 0 else np.inf)

    # -------- (A) MULTISCALE OPENERS --------
    fu_all = np.zeros(n, bool); fd_all = np.zeros(n, bool)
    for lb in LOOKBACKS:
        fu, fd, dup, ddn = _breaks(mid, A, sess, volok, bias_up, bias_dn, lb)
        if SIDE >= 0:
            for i in np.where(fu)[0]:
                emit(i, 1, mid[i] - RETR * dup[i])
        if SIDE <= 0:
            for i in np.where(fd)[0]:
                emit(i, -1, mid[i] + RETR * ddn[i])

    # -------- (B) INTRA-LEG RE-ARM on the primary lookback --------
    if REARM_ON:
        fu, fd, disp_up, disp_dn = _breaks(mid, A, sess, volok, bias_up, bias_dn, LEG_LB)
        if SIDE >= 0:
            leg = False; leg_high = -np.inf; rung_high = -np.inf; last_emit = -10**9; rungs = 0
            for i in range(n):
                if not leg:
                    if fu[i]:
                        leg = True; leg_high = mid[i]; rung_high = mid[i]
                        last_emit = i; rungs = 1
                    continue
                m = mid[i]
                if (not bias_up[i]) or (not sess[i]) or (m < leg_high - LEG_INVALID):
                    leg = False
                    continue
                if m > leg_high:
                    gap_ok = (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS
                    if gap_ok and (m - rung_high) >= EXT_PTS:
                        D = disp_up[i] if disp_up[i] > RETR_FLOOR * a0[i] else RETR_FLOOR * a0[i]
                        if RETR * D >= MIN_DEPTH:
                            emit(i, 1, m - RETR * D)
                            last_emit = i; rung_high = m; rungs += 1
                    leg_high = m
        if SIDE <= 0:
            leg = False; leg_low = np.inf; rung_low = np.inf; last_emit = -10**9; rungs = 0
            for i in range(n):
                if not leg:
                    if fd[i]:
                        leg = True; leg_low = mid[i]; rung_low = mid[i]
                        last_emit = i; rungs = 1
                    continue
                m = mid[i]
                if (not bias_dn[i]) or (not sess[i]) or (m > leg_low + LEG_INVALID):
                    leg = False
                    continue
                if m < leg_low:
                    gap_ok = (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS
                    if gap_ok and (rung_low - m) >= EXT_PTS:
                        D = disp_dn[i] if disp_dn[i] > RETR_FLOOR * a0[i] else RETR_FLOOR * a0[i]
                        if RETR * D >= MIN_DEPTH:
                            emit(i, -1, m + RETR * D)
                            last_emit = i; rung_low = m; rungs += 1
                    leg_low = m

    if not sig_i:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array(sig_i, np.int64)
    side = np.array(sig_side, np.int64)
    level = np.array(sig_level, np.float64)
    sl_pts = np.array(sig_sl, np.float64)
    tp_pts = np.array(sig_tp, np.float64)
    o = np.argsort(i, kind="stable")
    i, side, level, sl_pts, tp_pts = i[o], side[o], level[o], sl_pts[o], tp_pts[o]
    m = len(i)
    return Signals(i=i, side=side, kind=np.ones(m, int), level=level,
                   sl_pts=sl_pts, tp_pts=tp_pts, ttl=np.full(m, TTL, np.int64))
