"""Micro-BOS continuation, FREQUENCY-PUSHED (multi-scale displacement retest).

ROUND-2 MISSION: keep the proven micro-BOS continuation EDGE (strat_r3_1) while
raising frequency from ~1/day toward the 3-25/day band. The assigned lever was to
LOOSEN the gate (sweep K_DISP down, RETR, ATR band, session width) and map the
honest frequency<->PF frontier at a REALISTIC spread (judge ~0.25 taker).

WHAT ACTUALLY MOVED THE NEEDLE (vs the strat_r3_1 base, pf25~1.22 / 35 OOS trades):
  1. EXIT, not entry, is the dominant PF lever here. Widening the structure stop
     (SL 5->7) and the chandelier trail (4->6) let real continuation legs run and
     stopped clipping winners: at the SAME entry gate this lifted OOS pf25 from
     ~1.22 to ~1.6. That headroom is what made any loosening survivable.
  2. With the stronger exit, the entry gate can be loosened on the cheap dims:
       - shorter LOOKBACK (80->30) + a second, larger scale (120) => more distinct
         displacement-retest events;
       - shallower RETEST (RETR 0.30->0.15) => the limit fills on more of the breaks
         that run without a deep pullback.
  3. Stacking lookback scales [30,120] also IMPROVES PF (the larger scale confirms
     the smaller break) rather than just adding noise.

WHERE THE WALL IS (the honest frontier, OOS 2025-08..2026-06, taker, judged ~0.25):
  K_DISP is NON-NEGOTIABLE at 1.8. Every loosening of the QUALITY dims collapses the
  edge below the bar:
       K_DISP 1.2 (any hours)            -> pf25 ~0.7-0.8  (deeply negative, 200+ trades)
       hours widened past 7-15 (London+NY)-> pf25 < 1.0
       ATR_LO lowered                     -> no effect (not binding)
  The edge lives ONLY in K>=1.8 displacement during hours 7-15. Inside that regime,
  the CHEAP frequency dims (lookback scale count, retest depth, TTL) cap OOS trade
  count at ~45-49 while holding pf25>=1.3. The signal is SIGNAL-limited, not
  capacity-limited: the strat is flat >99% of the time, yet only ~49 genuine
  displacement-retest contexts exist in 11 OOS months. Pushing to the required
  >=100 OOS trades forces K_DISP down / hours wide, and pf25 drops under 1.0.

  CONCLUSION REPORTED HONESTLY: the >=100-OOS-trade (3-25/day) requirement is
  INCOMPATIBLE with PF>=1.3 at 0.25 taker for the micro-BOS family on XAU 5s. This
  config is the FREQUENCY-MAXIMISING point that still clears the edge bar:
       OOS taker  pf@0.20 ~1.41 , pf@0.30 ~1.30  => pf~0.25 ~1.35   (positive at 0.30)
       OOS trades ~49  (~1.3 / active-day; ~0.2 / calendar-day)
  i.e. a real, taker-survivable edge, but ~2x below the trade-count floor. Raising
  frequency further is possible only by trading edge for fills (frontier above).

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only (info up to bar i close):
roll_max/min exclude the current bar; M1-ATR aligns to the last COMPLETED M1 bar;
EMA bias is causal; the retest limit only fills on FORWARD bars; fresh-edge dedup
references the prior bar. No future indexing anywhere.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_mb_r1_freqpush"

# Exit management IS the edge enabler: wide structure stop + wide chandelier trail.
SIM = dict(maxhold=600, dollars_per_point=1.0, commission=0.07, cooldown=6,
           trail_pts=6.0, be_at_pts=0.0)

# --- tunable params (frequency-max config that still holds pf~0.25 taker >= 1.3) ---
LOOKBACKS = (30, 120)   # two structure scales -> more distinct break events + confirm
K_DISP    = 1.8         # displacement gate; HARD floor — below this the edge dies
RETR      = 0.15        # shallow retest -> fills the breaks that don't pull back deep
SL_PTS    = 7.0         # structure-wide stop (continuation invalidation)
TTL       = 150         # bars the retest limit stays live (~12.5 min)
ATR_LO    = 0.15        # skip dead tape  (M1 ATR pts)  -- not binding, kept for safety
ATR_HI    = 1.60        # skip runaway tape (M1 ATR pts)
BIAS_EMA  = 3600        # slow S5 EMA trend bias (~5h)
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active (UTC)


def _m1_atr_aligned(b: Bars):
    """Wilder ATR on M1 mid bars, aligned to S5 by the LAST COMPLETED M1 bar
    (causal). Length b.n; nan before the first M1 completes."""
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
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    bias_up = mid > Eb
    bias_dn = mid < Eb
    thr = K_DISP * A1

    i_all, s_all, lvl_all = [], [], []
    for LB in LOOKBACKS:
        rmax = roll_max(mid, LB)
        rmin = roll_min(mid, LB)
        disp_up = mid - rmax            # >0 when broken above prior LB extreme
        disp_dn = rmin - mid            # >0 when broken below
        brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
        brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn
        # fresh rising edge only (one signal per break event, per scale)
        fu = brk_up.copy(); fu[1:] &= ~brk_up[:-1]
        fd = brk_dn.copy(); fd[1:] &= ~brk_dn[:-1]
        iu = np.where(fu)[0]
        il = np.where(fd)[0]
        # maker retest: a shallow pullback into the displacement leg
        i_all.append(iu); s_all.append(np.ones(len(iu), int))
        lvl_all.append(mid[iu] - RETR * disp_up[iu])      # buy-limit dip (long)
        i_all.append(il); s_all.append(-np.ones(len(il), int))
        lvl_all.append(mid[il] + RETR * disp_dn[il])      # sell-limit pop (short)

    i = np.concatenate(i_all)
    side = np.concatenate(s_all)
    level = np.concatenate(lvl_all)
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(n, int),                # LIMIT maker entry at the retest
        level=level,
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, np.inf),           # trail-only exit (SIM.trail_pts rides leg)
        ttl=np.full(n, TTL, np.int64),
    )
