"""OTE (Optimal Trade Entry) displacement CONTINUATION on M1 (TF=60).

FAMILY (assigned): OTE continuation.
RULE SKETCH: after a displacement leg that shifts market structure (micro-BOS),
enter a with-trend continuation on the 0.62-0.79 fib RETRACE of that leg (the OTE
zone), bias-gated (slow M1 EMA) and kill-zone gated (London + NY). Structure stop
below the leg origin, chandelier trail so the continuation leg can run.

MECHANICS
---------
For a bullish leg at decision bar i:
  * micro-BOS + displacement: close[i] breaks above the prior-L swing high
    (roll_max(h,L)[i], excludes current bar) by >= K_DISP * ATR[i]  -> a real
    displacement leg, not drift.
  * leg origin  = roll_min(l,L)[i]  (lowest low of the last L bars, causal).
  * leg extreme = h[i]              (the breakout bar high).
  * OTE zone    = [H - 0.79*(H-Lo), H - 0.62*(H-Lo)]; rest a LIMIT LONG at a
    chosen fib DEPTH inside the zone (a discount retrace entry, level < close).
  * stop        = Lo - BUF_ATR*ATR[i] (below the origin that created the leg).
  * exit        = trail-only (tp=inf), chandelier via SIM.trail_pts.
Mirror for shorts (disabled by default: gold's 2024-26 uptrend kills OB/FVG shorts).

Frequency comes from a MULTISCALE UNION of leg lookbacks (each distinct break seeds
one OTE limit) + London+NY kill-zone hours, NOT from loosening the trigger. The
single-position engine serialises coincident breaks of the same leg.

NO LOOK-AHEAD (audited): roll_max/roll_min exclude the current bar (NaN warmup,
isfinite-gated); engine Wilder ATR is causal; EMA is past-only; the decision bar is
i (info up to close[i]) and the engine fills the limit only on bars i+1..i+TTL. The
OTE level is a fixed fib of quantities all known at close[i] (H=h[i], Lo=roll_min[i]).
No future bar is indexed. Absolute imports; TF drives the runner's M1 resample.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF=60.
RUN: .venv/Scripts/python.exe -m bot.micro.runner research/hunt/strat_m1_ote_displacement.py
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask, ema, fvg


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "m1_ote_displacement_cont"
TF = _P("OTE_TF", 60, int)     # M1 execution timeframe (seconds)

TRAIL = _P("OTE_TRAIL", 0.0)   # chandelier trail (pts) -> trail-only exit when >0
SIM = dict(maxhold=_P("OTE_MAXHOLD", 120, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("OTE_COOLDOWN", 0, int), trail_pts=TRAIL)

# multiscale leg lookbacks (M1 bars): each distinct micro-BOS seeds one OTE retest
LOOKBACKS = tuple(int(x) for x in os.environ.get("OTE_LBS", "18,26,36,50,70").split(","))
K_DISP   = _P("OTE_K", 1.10)          # displacement floor: close beyond swing >= K*ATR
# OTE fib depth inside the 0.62-0.79 zone (0.705 = canonical midpoint)
DEPTHS   = tuple(float(x) for x in os.environ.get("OTE_DEPTHS", "0.705").split(",") if x != "")
# fixed OTE target: leg extreme H + TGT_EXT*span (0.0 = back to the swing that was swept)
TGT_EXT  = _P("OTE_TGT", 0.0)
BUF_ATR  = _P("OTE_BUF", 0.30)        # stop buffer below leg origin, in ATR
TTL      = _P("OTE_TTL", 45, int)     # retest limit live bars (M1)
ATR_LO   = _P("OTE_ATRLO", 0.20)
ATR_HI   = _P("OTE_ATRHI", 30.0)
BIAS_EMA = _P("OTE_BIAS", 150, int)   # slow M1 EMA trend bias
SL_MIN   = _P("OTE_SLMIN", 1.0)       # floor on stop distance (pts)
SL_MAX   = _P("OTE_SLMAX", 12.0)      # cap on stop distance (pts) -> reject huge legs
SIDE     = _P("OTE_SIDE", 1, int)     # 0=both, 1=long-only, -1=short-only
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("OTE_HOURS", "7,8,9,10,11,12,13,14,15,16").split(","))
SLOPE    = _P("OTE_SLOPE", 5, int)     # EMA must slope with trade over this many bars (0=off)
FVG_REQ  = _P("OTE_FVG", 0, int)       # 1 = require an FVG overlapping the OTE zone


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
    if SLOPE > 0:
        Esl = np.zeros(n, bool); Esl[SLOPE:] = Eb[SLOPE:] > Eb[:-SLOPE]
        Edn = np.zeros(n, bool); Edn[SLOPE:] = Eb[SLOPE:] < Eb[:-SLOPE]
    else:
        Esl = np.ones(n, bool); Edn = np.ones(n, bool)
    bias_up = (c > Eb) & Esl
    bias_dn = (c < Eb) & Edn
    thr = K_DISP * A
    bull_fvg, bear_fvg, fvg_top, fvg_bot = fvg(o, h, l, c)
    # forward-fill the most recent FVG zone (causal), with a staleness age
    FVG_AGE = 30
    lb_top = np.full(n, np.nan); lb_bot = np.full(n, np.nan); lb_age = np.full(n, 1 << 30)
    ls_top = np.full(n, np.nan); ls_bot = np.full(n, np.nan); ls_age = np.full(n, 1 << 30)
    for i in range(n):
        if i > 0:
            lb_top[i] = lb_top[i-1]; lb_bot[i] = lb_bot[i-1]; lb_age[i] = lb_age[i-1] + 1
            ls_top[i] = ls_top[i-1]; ls_bot[i] = ls_bot[i-1]; ls_age[i] = ls_age[i-1] + 1
        if bull_fvg[i]:
            lb_top[i] = fvg_top[i]; lb_bot[i] = fvg_bot[i]; lb_age[i] = 0
        if bear_fvg[i]:
            ls_top[i] = fvg_top[i]; ls_bot[i] = fvg_bot[i]; ls_age[i] = 0

    sig_i = []; sig_side = []; sig_level = []; sig_sl = []; sig_tp = []

    def emit(i, sd, lo, hi):
        span = hi - lo
        if span <= 0:
            return
        A_i = A[i]
        for dpth in DEPTHS:
            if sd > 0:
                entry = hi - dpth * span          # discount retrace inside OTE zone
                sl = lo - BUF_ATR * A_i
                sl_pts = entry - sl
                tgt = hi + TGT_EXT * span          # OTE target: leg extreme (+ ext)
                tp_pts = tgt - entry
                if entry >= c[i]:                 # limit must sit below current price
                    continue
            else:
                entry = lo + dpth * span
                sl = hi + BUF_ATR * A_i
                sl_pts = sl - entry
                tgt = lo - TGT_EXT * span
                tp_pts = entry - tgt
                if entry <= c[i]:
                    continue
            if not (SL_MIN <= sl_pts <= SL_MAX):
                continue
            if tp_pts <= 0:
                continue
            if FVG_REQ:
                if sd > 0:
                    if not (lb_age[i] <= FVG_AGE and np.isfinite(lb_bot[i])
                            and lb_bot[i] <= entry <= lb_top[i]):
                        continue
                else:
                    if not (ls_age[i] <= FVG_AGE and np.isfinite(ls_bot[i])
                            and ls_bot[i] <= entry <= ls_top[i]):
                        continue
            tp_out = np.inf if TRAIL > 0 else tp_pts
            sig_i.append(int(i)); sig_side.append(sd); sig_level.append(entry)
            sig_sl.append(sl_pts); sig_tp.append(tp_out)

    fu_any = np.zeros(n, bool); fd_any = np.zeros(n, bool)
    lo_at = np.full(n, np.nan); hi_at = np.full(n, np.nan)
    lo_at_d = np.full(n, np.nan); hi_at_d = np.full(n, np.nan)
    for L in LOOKBACKS:
        rmax = roll_max(h, L); rmin = roll_min(l, L)
        okv = np.isfinite(A) & volok & sess
        bu = np.isfinite(rmax) & okv & (c - rmax >= thr) & bias_up
        bd = np.isfinite(rmin) & okv & (rmin - c >= thr) & bias_dn
        e_u = bu.copy(); e_u[1:] &= ~bu[:-1]     # only fresh break edges
        e_d = bd.copy(); e_d[1:] &= ~bd[:-1]
        for i in np.where(e_u)[0]:
            lo = rmin[i]                          # leg origin (causal min of prior L)
            if np.isfinite(lo):
                emit(i, 1, lo, h[i])
        for i in np.where(e_d)[0]:
            hi = rmax[i]
            if np.isfinite(hi):
                emit(i, -1, l[i], hi)

    if SIDE > 0:
        keep = [k for k in range(len(sig_side)) if sig_side[k] > 0]
    elif SIDE < 0:
        keep = [k for k in range(len(sig_side)) if sig_side[k] < 0]
    else:
        keep = list(range(len(sig_side)))

    if not keep:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array([sig_i[k] for k in keep], np.int64)
    side = np.array([sig_side[k] for k in keep], np.int64)
    level = np.array([sig_level[k] for k in keep], np.float64)
    sl_pts = np.array([sig_sl[k] for k in keep], np.float64)
    tp_pts = np.array([sig_tp[k] for k in keep], np.float64)
    ord_ = np.argsort(i, kind="stable")
    i, side, level, sl_pts, tp_pts = i[ord_], side[ord_], level[ord_], sl_pts[ord_], tp_pts[ord_]
    m = len(i)
    return Signals(i=i, side=side, kind=np.ones(m, int), level=level,
                   sl_pts=sl_pts, tp_pts=tp_pts, ttl=np.full(m, TTL, np.int64))
