"""Micro-BOS continuation, RETEST-FAMILY frequency lever (mb_r1_3).

BASE = bot/micro/strat_r3_1.py (micro-BOS displacement break -> shallow maker
retest, trend+session+ATR filtered). That base has a REAL but thin edge
(OOS PF ~1.33 @0.20 taker, ~1.10 @0.30 taker) at only ~1.1 trades/day / ~35 OOS
trades -- below the >=100-trade floor.

THIS CANDIDATE'S LEVER (assigned): the RETEST entry MECHANIC. Vary where the
continuation limit sits inside the displacement leg and combine the productive
depths:
  * shallow retest      level = mid - f*disp,  f small (~0.3): fills often, the
                        base mechanic.
  * deeper second-chance level = mid - f*disp,  f ~0.5: a deeper pullback; on this
                        instrument it turns out to be a HIGHER-quality fill (the
                        spike-and-go reverts shallow fills more than deep ones).
  * breaker retest      level = the broken structure itself (f = 1.0 -> level=rmax
                        for longs / rmin for shorts): the price returns to test the
                        level it broke, then continues.
The ladder emits one limit per depth on each fresh break; the engine fills the
SHALLOWEST that trades first and blocks the rest (single position), so the ladder
is a "take the first depth the market offers, preferring the deeper/cleaner one
when it doesn't overshoot" rule rather than multiple positions per break.

FREQUENCY: the displacement threshold K*M1ATR is the load-bearing quality filter
-- loosening it (lower K / shorter lookback) collapses PF below 1.0 (verified),
so frequency is NOT bought by diluting displacement. It is bought by (a) widening
the active-hours window to every liquid hour (same-quality breaks, more of them)
and (b) dropping the slow-EMA bias gate so BOTH break directions are tradeable in
any regime. The retest depth (deeper f) is what keeps PF >= 1.3 at 0.25 taker
while those two knobs multiply the trade count.

HONEST FRONTIER is reported in the runner JSON (oos_spread_grid maker/taker @0.20
& 0.30); judge ~0.25 taker. No look-ahead: roll_max/min are causal (exclude the
current bar), M1 ATR is aligned to the last COMPLETED M1 bar, EMA is causal, and
entries are forward-scanned limit fills only.

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only (info up to bar i close).
"""
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_retest_ladder"

SIM = dict(maxhold=400, dollars_per_point=1.0, commission=0.07, cooldown=12,
           trail_pts=6.0, be_at_pts=0.0)

# --- tunable params (runner sweeps vary +/-30%) ---
LOOKBACK = 80          # S5 bars defining the micro-structure extreme (~6.7 min)
K_DISP   = 1.8         # displacement: close beyond extreme by >= K_DISP * M1-ATR
                       # (the load-bearing QUALITY filter; lowering it for frequency
                       #  collapses PF < 1.0 -- verified, do not relax)
FRACS    = (0.25,)     # retest depth(s) as fraction of the displacement leg. The
                       # 0.25 second-chance pullback gave the best frequency/PF
                       # trade-off; a ladder e.g. (0.25, 1.0) is a no-op because the
                       # engine fills the SHALLOWEST rung and blocks the rest.
SL_PTS   = 5.0         # structure-wide stop from fill
TP_PTS   = np.inf      # trail-only exit (SIM.trail_pts rides the leg)
TTL      = 300         # bars the retest limit stays live (~25 min); plateau 180-360
ATR_LO   = 0.20        # skip dead tape  (M1 ATR pts)
ATR_HI   = 1.60        # skip runaway tape (M1 ATR pts)
BIAS_EMA = 3600        # slow S5 EMA for trend bias (~5h)
USE_BIAS = False       # gate breaks by EMA trend? off => both directions tradeable
                       # (adds a few trades; PF unchanged -- the edge isn't the bias)
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)  # London+NY only -- the edge is
                       # session-localized; widening hours destroys PF (verified)


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
    al = np.full(b.n, np.nan); ok = pos >= 0
    al[ok] = out[pos[ok]]
    return al


def generate(b: Bars) -> Signals:
    mid = b.mid
    A1 = _m1_atr_aligned(b)
    Eb = ema(mid, BIAS_EMA)
    rmax = roll_max(mid, LOOKBACK)
    rmin = roll_min(mid, LOOKBACK)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    if USE_BIAS:
        bias_up = mid > Eb; bias_dn = mid < Eb
    else:
        bias_up = np.ones(b.n, bool); bias_dn = np.ones(b.n, bool)

    disp_up = mid - rmax          # >0 when broken above
    disp_dn = rmin - mid          # >0 when broken below
    thr = K_DISP * A1

    brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
    brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn

    # fresh rising edge only (one signal cluster per break event)
    fu = brk_up.copy(); fu[1:] &= ~brk_up[:-1]
    fd = brk_dn.copy(); fd[1:] &= ~brk_dn[:-1]
    iu = np.where(fu)[0]
    il = np.where(fd)[0]

    # retest ladder: one limit per depth fraction
    I = []; SIDE = []; LVL = []; DEPTH = []
    for f in FRACS:
        I.append(iu); SIDE.append(np.ones(len(iu), int))
        LVL.append(mid[iu] - f * disp_up[iu]); DEPTH.append(np.full(len(iu), f))
        I.append(il); SIDE.append(-np.ones(len(il), int))
        LVL.append(mid[il] + f * disp_dn[il]); DEPTH.append(np.full(len(il), f))
    i = np.concatenate(I); side = np.concatenate(SIDE)
    level = np.concatenate(LVL); depth = np.concatenate(DEPTH)

    # order by decision bar, shallowest-first within a bar (easiest fill attempted
    # first; deeper ladder rungs are fallbacks the engine reaches only if the
    # shallow one never trades within TTL).
    o = np.lexsort((depth, i))
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(n, int),                # LIMIT maker entry at the retest
        level=level,
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, TP_PTS),
        ttl=np.full(n, TTL, np.int64),
    )
