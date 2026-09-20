"""Micro-BOS continuation, MULTI-SCALE (the frequency lever for round 2).

BASE EDGE (unchanged from strat_r3_1): a DISPLACEMENT break of micro-structure
(mid close beyond the last LOOKBACK-bar extreme by >= K * M1-ATR) followed by a
shallow retrace; enter the continuation on a MAKER limit retest inside the
displacement leg, trend-aligned (slow EMA), session-gated, ATR-banded, with a
structure-wide stop and a trailing exit so a real leg can run. One order per
fresh break edge.

THE LEVER (this file): run the SAME causal detector at SEVERAL lookbacks at once
(e.g. 30/60/120/240 S5 bars) and union the resulting retest orders. A break of a
near extreme (small lookback) and a break of a far extreme (large lookback) are
DIFFERENT structural events; unioning them multiplies the number of independent
break contexts without changing the logic. Frequency rises; the engine's
single-position + cooldown rule prevents double-counting overlapping breaks, and
the maker-limit + displacement + bias + session filters keep quality.

NO LOOK-AHEAD: every input (roll_max/min causal, M1 ATR aligned to the last
completed M1 bar, EMA causal). Each scale's break is detected at bar i from
info <= close[i]; the retest limit is then worked forward by the engine.

CONTRACT: generate(b)->Signals ; SIM ; NAME.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_multiscale"

SIM = dict(maxhold=600, dollars_per_point=1.0, commission=0.07, cooldown=12,
           trail_pts=4.0, be_at_pts=0.0)

# --- multi-scale structure lookbacks (S5 bars) ---
# HONEST RESULT OF THE LEVER (see footer): the edge lives ONLY in LARGE-structure
# breaks (PF rises monotonically with lookback: lb80=1.33, lb240=1.86 @0.20 taker);
# small lookbacks add net-LOSING trades. Worse, large breaks COINCIDE in time, so
# the single-position rule dedups the union -> unioning many scales does NOT raise
# frequency. The widest passing config is ~31 trades. We ship the two strong
# large scales (20-min + 40-min) as the genuine multi-scale; it adds ~1 trade over
# lb=240 alone while keeping a wide PF margin (robustness over reach).
LOOKBACKS = (240, 480)   # ~20 min + ~40 min structural extremes

# --- shared signal params (same family as the proven base) ---
K_DISP   = 1.8        # displacement: close beyond extreme by >= K_DISP * M1-ATR
RETR     = 0.30       # retest depth: limit at break - RETR*disp (shallow pullback)
SL_PTS   = 5.0        # structure-wide stop from fill
TP_PTS   = np.inf     # trail-only exit (SIM.trail_pts rides the leg)
TTL      = 90         # bars the retest limit stays live (~7.5 min)
ATR_LO   = 0.20       # skip dead tape  (M1 ATR pts)
ATR_HI   = 1.60       # skip runaway tape (M1 ATR pts)
BIAS_EMA = 3600       # slow S5 EMA for trend bias (~5h)
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active (UTC)


def _m1_atr_aligned(b: Bars):
    """Wilder ATR on M1 mid bars, aligned to S5 by the LAST COMPLETED M1 bar."""
    r = resample(b, 60)
    h, l, c = r["h"], r["l"], r["c"]
    pc = np.empty_like(c); pc[0] = c[0]; pc[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    a = 1.0 / 14.0
    out = np.empty_like(tr); out[0] = tr[0]
    for i in range(1, len(tr)):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
    s5idx = r["s5_idx"]
    pos = np.searchsorted(s5idx, np.arange(b.n), side="right") - 1
    al = np.full(b.n, np.nan)
    ok = pos >= 0
    al[ok] = out[pos[ok]]
    return al


def _breaks_at(mid, A1, sess, volok, bias_up, bias_dn, lookback):
    """Return (idx_up, lvl_up, idx_dn, lvl_dn) fresh-edge displacement breaks of
    the LOOKBACK-bar micro extreme, with the maker retest level for each."""
    rmax = roll_max(mid, lookback)
    rmin = roll_min(mid, lookback)
    disp_up = mid - rmax
    disp_dn = rmin - mid
    thr = K_DISP * A1
    brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
    brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn
    fu = brk_up.copy(); fu[1:] &= ~brk_up[:-1]
    fd = brk_dn.copy(); fd[1:] &= ~brk_dn[:-1]
    iu = np.where(fu)[0]
    il = np.where(fd)[0]
    lvl_u = mid[iu] - RETR * disp_up[iu]
    lvl_d = mid[il] + RETR * disp_dn[il]
    return iu, lvl_u, il, lvl_d


def generate(b: Bars) -> Signals:
    mid = b.mid
    A1 = _m1_atr_aligned(b)
    Eb = ema(mid, BIAS_EMA)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    bias_up = mid > Eb
    bias_dn = mid < Eb

    iu_all, lu_all, il_all, ld_all = [], [], [], []
    for lb in LOOKBACKS:
        iu, lu, il, ld = _breaks_at(mid, A1, sess, volok, bias_up, bias_dn, lb)
        iu_all.append(iu); lu_all.append(lu); il_all.append(il); ld_all.append(ld)

    iu = np.concatenate(iu_all) if iu_all else np.array([], int)
    lu = np.concatenate(lu_all) if lu_all else np.array([], float)
    il = np.concatenate(il_all) if il_all else np.array([], int)
    ld = np.concatenate(ld_all) if ld_all else np.array([], float)

    i = np.concatenate([iu, il])
    side = np.concatenate([np.ones(len(iu), int), -np.ones(len(il), int)])
    level = np.concatenate([lu, ld])
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(n, int),
        level=level,
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, TP_PTS),
        ttl=np.full(n, TTL, np.int64),
    )
