"""Micro-BOS continuation (MAKER retest, trend-aligned, trail-ridden).

ASSIGNED CONCEPT: a DISPLACEMENT break of micro-structure (mid close beyond the
last N-bar extreme by >= K * M1-ATR) followed by a SHALLOW retrace; enter the
continuation on the retest (a maker limit inside the displacement leg), NOT on the
breakout. Only ONE order per fresh break edge, only WITH a slow-EMA trend, only in
the active London/NY sessions, with a structure-wide stop and a trailing exit so a
real continuation leg can run instead of being clipped in a few minutes.

WHY IT'S BUILT THIS WAY (vs the prior dead ends micro_bos_cont / micro_bos_retest,
which were taker, unfiltered, 12-25 trades/day and lost thousands):
  * Maker limit at the retest earns rather than pays the ~0.3-0.66pt spread, and is
    the natural fill for "enter on the retest."
  * Fresh-edge + displacement>=K*ATR + EMA-bias + session + ATR-band cut frequency to
    the rare, trend-aligned context the scout notes said the edge would have to live in.
  * SL beyond the structure + trailing TP lets the trend continuation actually run.

HONEST RESULT (this is the deliverable, not a pass). Measured on real S5 ticks,
train 2024-01..2025-07, OOS 2025-08..2026-06, plus a 1.5x-cost stress pass:
  Micro-BOS continuation has NO edge on XAU 5s, in EITHER execution mode or either
  direction. Across a wide sweep (LOOKBACK 40-240, K 1.2-3.0, maker/taker, shallow
  /deep retest, fixed/trailing exits, bias on/off) TRAIN profit factor never leaves
  0.4-0.6 and net is always deeply negative; post-break short-horizon excursion is
  ANTI-continuation (WR ~20-36% at RR>1 = worse than a random walk -> the spike
  reverts). The only configs whose OOS net brushes zero are themselves train-negative
  (selection noise, not a parameter plateau). Frequency also sits ~1 trade/day, below
  the 3-25 floor; loosening the filters to raise it collapses PF further. This is a
  trend-aligned continuation that still loses INSIDE the dominant 2024-25 uptrend,
  which is the strongest possible refutation of the idea on this instrument/timeframe.
  Conclusion: micro-BOS continuation is dead here (consistent with all prior
  micro_bos / sweep dead ends). Not deployable; reported for the evidence.

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only (info up to bar i close).
"""
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_cont_maker"

SIM = dict(maxhold=600, dollars_per_point=1.0, commission=0.07, cooldown=12,
           trail_pts=4.0, be_at_pts=0.0)

# --- tunable params (least-bad honest config; runner sweeps vary ±30%) ---
LOOKBACK = 80         # S5 bars defining the micro-structure extreme (~6.7 min)
K_DISP   = 1.8        # displacement: close beyond extreme by >= K_DISP * M1-ATR
RETR     = 0.30       # retest depth: limit at mid - RETR*disp (shallow pullback)
SL_PTS   = 5.0        # structure-wide stop from fill (continuation invalidation)
TP_PTS   = np.inf     # trail-only exit (SIM.trail_pts rides the leg)
TTL      = 90         # bars the retest limit stays live (~7.5 min)
ATR_LO   = 0.20       # skip dead tape  (M1 ATR pts)
ATR_HI   = 1.60       # skip runaway tape (M1 ATR pts)
BIAS_EMA = 3600       # slow S5 EMA for trend bias (~5h)
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active (UTC)


def _m1_atr_aligned(b: Bars):
    """Wilder ATR on M1 mid bars, aligned to S5 by the LAST COMPLETED M1 bar
    (causal). Returns array length b.n (nan before the first M1 completes)."""
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


def generate(b: Bars) -> Signals:
    mid = b.mid
    A1 = _m1_atr_aligned(b)
    Eb = ema(mid, BIAS_EMA)
    rmax = roll_max(mid, LOOKBACK)
    rmin = roll_min(mid, LOOKBACK)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    bias_up = mid > Eb
    bias_dn = mid < Eb

    disp_up = mid - rmax          # >0 when broken above
    disp_dn = rmin - mid          # >0 when broken below
    thr = K_DISP * A1

    brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
    brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn

    # fresh rising edge only (one signal per break event)
    fu = brk_up.copy(); fu[1:] &= ~brk_up[:-1]
    fd = brk_dn.copy(); fd[1:] &= ~brk_dn[:-1]

    iu = np.where(fu)[0]
    il = np.where(fd)[0]

    # maker retest level: a shallow pullback into the displacement leg
    lvl_u = mid[iu] - RETR * disp_up[iu]     # buy-limit dip (continuation long)
    lvl_d = mid[il] + RETR * disp_dn[il]     # sell-limit pop (continuation short)

    i = np.concatenate([iu, il])
    side = np.concatenate([np.ones(len(iu), int), -np.ones(len(il), int)])
    level = np.concatenate([lvl_u, lvl_d])
    o = np.argsort(i, kind="stable")
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
