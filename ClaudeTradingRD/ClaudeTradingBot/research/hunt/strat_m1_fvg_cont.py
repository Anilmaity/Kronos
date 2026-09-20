"""FVG CONTINUATION on M1 — with-trend retest into a fresh displacement FVG.
(assignment: FVG continuation family, TF=M1, target ~3-6 trades/day)

CONCEPT
-------
A 3-bar fair-value gap prints in the higher-TF bias direction. We do NOT chase
the impulse: we rest a LIMIT at the retest INTO the gap (a with-trend pullback
into the freshly-created imbalance = continuation support/resistance), with a
structure-wide stop just beyond the FAR gap edge and a chandelier TRAIL so the
continuation leg can run. The M5 EMA bias (+slope) and a gap-size displacement
floor keep only genuine with-trend continuations.

ROBUSTNESS TILT vs the prior both-sided lead (strat_m1_r3_5)
------------------------------------------------------------
The prior both-sided FVG-fill was OOS-strong but FAILED the 1.5x stress pass and
went flat in 2024 — its short side loses in gold's 2024-26 uptrend. This build is
LONG-ONLY (SIDE=1) and adds an optional break-of-structure confirmation on the
displacement bar, aiming to hold up per-year and through the cost stress.

FREQUENCY
---------
Reached via the London+NY kill-zone hour set and (optionally) two fill depths per
gap so distinct pullbacks into one displacement each get a resting limit — NOT by
loosening the gap / bias / displacement gates (those are the edge, not knobs).

CAUSALITY (audited, no look-ahead)
----------------------------------
TF=60 -> runner feeds M1 bars. The M1 FVG at bar i uses bars i-2,i-1,i, confirmed
at CLOSE of i; the LIMIT is placed for bars STRICTLY AFTER i (engine scans
di+1..di+ttl). The M5 EMA bias is computed on a resample of the M1 bars and
broadcast to each M1 bar ONLY from the last FULLY-COMPLETED M5 bar (value of HTF
bar k applies to M1 indices > s5_idx[k]). roll_max/roll_min exclude the current
bar (NaN warmup, np.isfinite-gated); atr Wilder-causal; ema past-only. No future
bar indexed; decision bar i, engine fills i+1 onward.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str ; TF=60
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import resample, fvg, ema, hours_mask


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "m1_fvg_cont_nearedge"
TF = 60   # M1 execution timeframe (seconds)

TRAIL = _P("FVG_TRAIL", 0.8)
SIM = dict(maxhold=_P("FVG_MAXHOLD", 60, int), dollars_per_point=1.0,
           commission=0.07, cooldown=_P("FVG_COOLDOWN", 2, int), trail_pts=TRAIL)

# --- HTF (M5) EMA bias ---
HTF_SEC   = _P("FVG_HTF", 300, int)
EMA_P     = _P("FVG_EMAP", 50, int)
EMA_SLOPE = _P("FVG_SLOPE", 3, int)

# --- displacement / FVG gate ---
GAP_MIN  = _P("FVG_GAPMIN", 2.6)    # displacement floor: high enough to stay TRAIN-robust
GAP_MAX  = _P("FVG_GAPMAX", 6.0)
ATR_P    = _P("FVG_ATRP", 14, int)
BUF_ATR  = _P("FVG_BUF", 0.5)
K_DISP   = _P("FVG_K", 0.0)         # optional BOS: close beyond prior-BRK extreme by K*ATR (0=off)
BRK_LB   = _P("FVG_BRK", 20, int)
DEPTHS   = tuple(float(x) for x in os.environ.get("FVG_DEPTHS", "0.5").split(",") if x != "")
TTL      = _P("FVG_TTL", 25, int)
SL_MIN   = _P("FVG_SLMIN", 1.0)
SL_MAX   = _P("FVG_SLMAX", 12.0)
SIDE     = _P("FVG_SIDE", 0, int)   # 0=both, 1=long-only, -1=short-only
# full London+NY kill-zone hour set: frequency comes from MORE sessions, not a
# lower gap floor (loosening the floor tilts the edge to 2026 and breaks TRAIN).
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("FVG_HOURS", "7,8,9,10,11,12,13,14,15,16").split(","))


def _htf_to_m1(n, s5_idx, val):
    out = np.full(n, np.nan)
    K = len(val)
    for k in range(K):
        start = int(s5_idx[k]) + 1
        end = int(s5_idx[k + 1]) + 1 if k + 1 < K else n
        if start < n:
            out[start:min(end, n)] = val[k]
    return out


def _empty():
    z = np.zeros(0)
    return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)


def generate(b: Bars) -> Signals:
    n = b.n
    o = (b.ao + b.bo) * 0.5
    h = (b.ah + b.bh) * 0.5
    l = (b.al + b.bl) * 0.5
    c = b.mid

    R = resample(b, HTF_SEC)
    Hc = R["c"]; s5idx = R["s5_idx"]; K = len(Hc)
    if K <= EMA_P + EMA_SLOPE + 1:
        return _empty()
    Eh = ema(Hc, EMA_P)
    bu = np.zeros(K, np.int8); bd = np.zeros(K, np.int8)
    for k in range(EMA_SLOPE, K):
        if Hc[k] > Eh[k] and Eh[k] > Eh[k - EMA_SLOPE]:
            bu[k] = 1
        elif Hc[k] < Eh[k] and Eh[k] < Eh[k - EMA_SLOPE]:
            bd[k] = 1
    bias_up = _htf_to_m1(n, s5idx, bu)
    bias_dn = _htf_to_m1(n, s5idx, bd)

    A = atr(b, ATR_P)
    bull, bear, top, bot = fvg(o, h, l, c)
    sess = hours_mask(b, np.array(SESSION_HOURS))
    pri_hi = roll_max(h, BRK_LB)
    pri_lo = roll_min(l, BRK_LB)

    I, SIDE_, LVL, SLP, TPP = [], [], [], [], []
    for i in range(2, n):
        if not sess[i] or i + 1 >= n:
            continue
        gsz = top[i] - bot[i]
        if not np.isfinite(gsz) or not (GAP_MIN <= gsz <= GAP_MAX):
            continue
        a = A[i]
        if not np.isfinite(a) or a <= 0:
            continue
        thr = K_DISP * a

        if (SIDE >= 0) and bull[i] and bias_up[i] == 1 and \
                (K_DISP <= 0 or (np.isfinite(pri_hi[i]) and c[i] - pri_hi[i] >= thr)):
            for dpth in DEPTHS:
                level = top[i] - dpth * gsz     # dip into the bull gap (with-trend support)
                stop = bot[i] - BUF_ATR * a
                sl_dist = level - stop
                if level >= c[i] or not (SL_MIN <= sl_dist <= SL_MAX):
                    continue
                I.append(i); SIDE_.append(1); LVL.append(level)
                SLP.append(sl_dist); TPP.append(np.inf)

        elif (SIDE <= 0) and bear[i] and bias_dn[i] == 1 and \
                (K_DISP <= 0 or (np.isfinite(pri_lo[i]) and pri_lo[i] - c[i] >= thr)):
            for dpth in DEPTHS:
                level = bot[i] + dpth * gsz
                stop = top[i] + BUF_ATR * a
                sl_dist = stop - level
                if level <= c[i] or not (SL_MIN <= sl_dist <= SL_MAX):
                    continue
                I.append(i); SIDE_.append(-1); LVL.append(level)
                SLP.append(sl_dist); TPP.append(np.inf)

    if not I:
        return _empty()
    I = np.array(I, np.int64)
    order = np.argsort(I, kind="stable")
    m = len(I)
    return Signals(
        i=I[order],
        side=np.array(SIDE_, np.int64)[order],
        kind=np.ones(m, np.int64),
        level=np.array(LVL, np.float64)[order],
        sl_pts=np.array(SLP, np.float64)[order],
        tp_pts=np.array(TPP, np.float64)[order],
        ttl=np.full(m, TTL, np.int64),
    )
