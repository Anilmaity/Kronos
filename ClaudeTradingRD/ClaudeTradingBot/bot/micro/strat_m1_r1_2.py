"""M1 LIQUIDITY-SWEEP REVERSAL (turtle soup), vectorized.

CONCEPT (distinct from the micro-BOS *continuation* family in FINDINGS.md):
A sweep of GENUINE RESTING LIQUIDITY -- a confirmed swing high/low that HELD -- that
runs counter to the higher-timeframe trend, then RECLAIMS back through the level with
a rejection wick. We trade the reclaim WITH the trend (stop-hunt above a high in a
down-bias -> resume down; mirror for longs). Stop just beyond the sweep extreme (where
the stop-run truly invalidates); exit via fixed-R target into the range interior, or a
trailing stop to ride the reversion. M1 bars (~2pt) give the move room to clear cost.

WHY THIS CAN HAVE ASYMMETRY WHERE A BARE FADE DOESN'T (scout #2/#3): a generic
rolling-extreme fade is symmetric (MFE~MAE) = knife-catching. Here the trigger is
narrowed to (a) a confirmed-and-held swing level = real resting liquidity, (b) a
*marginal* sweep that grabs stops then (c) reclaims with a rejection wick, and (d) the
sweep is COUNTER-trend so the reversal resumes the dominant flow. That conjunction is
where favorable>>adverse can appear.

NO LOOK-AHEAD: swings() centered (k each side) -> a swing at j is referenced only from
its confirm bar j+K (the active resting level at bar i is the most-recent level
confirmed at/<= i, via causal forward-fill). ATR/EMA causal. Entries act on bars AFTER
the sweep bar, filled by the engine next-bar+. Absolute imports.
Contract: generate(b)->Signals, SIM, NAME, TF.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr as atr_fn
from bot.micro.features import swings, hours_mask, ema

NAME = "m1_sweep_reversal"
TF = 60   # M1


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


KIND     = _P("SR_KIND", 1, int)         # 0=market on reclaim bar, 1=limit retest at level
TRAIL    = _P("SR_TRAIL", 0.0)           # >0 -> trailing stop (pts); target becomes interior cap
SIM = dict(maxhold=_P("SR_MAXHOLD", 40, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("SR_COOLDOWN", 2, int), trail_pts=TRAIL)

K        = _P("SR_K", 3, int)            # fractal half-width for swings
ATR_P    = _P("SR_ATRP", 20, int)        # M1 ATR period
SWEEP_BUF= _P("SR_SWBUF", 0.05)          # sweep must exceed level by >= this * ATR
DISP_K   = _P("SR_DISP", 0.80)           # rejection wick (hi-close) >= DISP_K * ATR
SL_BUF   = _P("SR_SLBUF", 0.35)          # stop sits SL_BUF*ATR beyond the sweep extreme
TP_R     = _P("SR_TPR", 1.8)             # target = TP_R * stop distance (interior)
TTL      = _P("SR_TTL", 10, int)         # retest limit lifetime (M1 bars) -- KIND=1 only
SL_MIN   = _P("SR_SLMIN", 1.2)           # skip if stop distance < this (pts)
SL_MAX   = _P("SR_SLMAX", 7.0)           # skip if stop distance > this (pts) -- huge sweep
ATR_LO   = _P("SR_ATRLO", 0.6)           # min M1 ATR (avoid dead tape)
ATR_HI   = _P("SR_ATRHI", 12.0)
BIAS_EMA = _P("SR_BIAS", 120, int)       # 0=off; slow EMA trend filter (M1 bars)
LEVEL_MAXAGE = _P("SR_MAXAGE", 90, int)  # resting level must be younger than this (bars)
RECLAIM_K= _P("SR_RECK", 0.0)            # close must be >= RECLAIM_K*ATR back inside the level
SIDE_ONLY= _P("SR_SIDE", 0, int)         # 0=both, 1=long-only, -1=short-only
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("SR_HOURS", "7,8,9,10,11,12,13,14").split(","))


def _ffill(x):
    """Causal forward-fill of a 1-D array with NaNs; returns (filled, src_index)."""
    n = len(x)
    valid = ~np.isnan(x)
    idx = np.where(valid, np.arange(n), -1)
    np.maximum.accumulate(idx, out=idx)
    filled = np.where(idx >= 0, x[idx.clip(min=0)], np.nan)
    return filled, idx


def generate(b: Bars) -> Signals:
    n = b.n
    if n < 5 * K + 10:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    c  = b.mid
    A  = atr_fn(b, ATR_P)
    a  = np.where(np.isfinite(A) & (A > 0), A, np.nan)
    sess = hours_mask(b, SESSION_HOURS)
    volok = np.isfinite(a) & (a >= ATR_LO) & (a <= ATR_HI)
    Eb = ema(c, BIAS_EMA) if BIAS_EMA > 0 else None

    sh, slw = swings(hi, lo, K)               # centered fractal swings

    # active resting HIGH level: set at confirm bar j+K to hi[j], then forward-fill.
    lvlH = np.full(n, np.nan); lvlL = np.full(n, np.nan)
    for j in np.where(sh)[0]:
        t = j + K
        if t < n:
            lvlH[t] = hi[j]
    for j in np.where(slw)[0]:
        t = j + K
        if t < n:
            lvlL[t] = lo[j]
    lvlH_ff, cidxH = _ffill(lvlH)
    lvlL_ff, cidxL = _ffill(lvlL)
    ageH = np.arange(n) - cidxH
    ageL = np.arange(n) - cidxL

    base = sess & volok

    def _first_per_group(mask, cidx):
        si = np.where(mask)[0]
        if len(si) == 0:
            return si
        keep = np.ones(len(si), bool)
        keep[1:] = cidx[si[1:]] != cidx[si[:-1]]
        return si[keep]

    # FRESHNESS: only the FIRST genuine sweep-touch of each resting level is eligible
    # (an untested level whose first stop-run failed = the turtle-soup context). A
    # level whose first touch does NOT reclaim is discarded, not retried.
    touchH = base & np.isfinite(lvlH_ff) & (cidxH >= 0) & (ageH <= LEVEL_MAXAGE) \
        & (hi >= lvlH_ff + SWEEP_BUF * a)
    touchL = base & np.isfinite(lvlL_ff) & (cidxL >= 0) & (ageL <= LEVEL_MAXAGE) \
        & (lo <= lvlL_ff - SWEEP_BUF * a)
    ftH = _first_per_group(touchH, cidxH)
    ftL = _first_per_group(touchL, cidxL)

    sldH = (hi - lvlH_ff) + SL_BUF * a
    sldL = (lvlL_ff - lo) + SL_BUF * a

    # ---- SHORT: first sweep of resting high reclaims below, down-bias ----
    okH = (c[ftH] <= lvlH_ff[ftH] - RECLAIM_K * a[ftH]) \
        & ((hi[ftH] - c[ftH]) >= DISP_K * a[ftH]) \
        & (sldH[ftH] >= SL_MIN) & (sldH[ftH] <= SL_MAX)
    if BIAS_EMA > 0:
        okH &= (c[ftH] < Eb[ftH])
    iH = ftH[okH]
    if SIDE_ONLY > 0:
        iH = iH[:0]

    # ---- LONG: first sweep of resting low reclaims above, up-bias ----
    okL = (c[ftL] >= lvlL_ff[ftL] + RECLAIM_K * a[ftL]) \
        & ((c[ftL] - lo[ftL]) >= DISP_K * a[ftL]) \
        & (sldL[ftL] >= SL_MIN) & (sldL[ftL] <= SL_MAX)
    if BIAS_EMA > 0:
        okL &= (c[ftL] > Eb[ftL])
    iL = ftL[okL]
    if SIDE_ONLY < 0:
        iL = iL[:0]

    if len(iH) + len(iL) == 0:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.concatenate([iH, iL])
    side = np.concatenate([-np.ones(len(iH), np.int64), np.ones(len(iL), np.int64)])
    if KIND == 1:                              # limit retest at the reclaimed level
        level = np.concatenate([lvlH_ff[iH], lvlL_ff[iL]])
    else:                                      # market on reclaim bar (level ignored)
        level = np.concatenate([c[iH], c[iL]])
    slp = np.concatenate([sldH[iH], sldL[iL]])
    tpp = TP_R * slp
    if TRAIL > 0:
        tpp = np.full(len(i), np.inf)          # trail-only: ride the reversion

    o = np.argsort(i, kind="stable")
    i, side, level, slp, tpp = i[o], side[o], level[o], slp[o], tpp[o]
    m = len(i)
    return Signals(i=i, side=side, kind=np.full(m, KIND, np.int8), level=level,
                   sl_pts=slp, tp_pts=tpp, ttl=np.full(m, TTL, np.int64))
