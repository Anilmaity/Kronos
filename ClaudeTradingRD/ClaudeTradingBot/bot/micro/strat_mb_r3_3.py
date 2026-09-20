"""Micro-BOS continuation, MULTI-SCALE + retest-depth LADDER (the frequency lever).

ASSIGNED LEVER: run the proven micro-BOS displacement-break + maker-retest detector
(strat_r3_1) at SEVERAL structure LOOKBACKs at once and union the signals, so more
independent break contexts produce more trades with the identical edge logic.

WHAT THE MULTI-SCALE SWEEP ACTUALLY SHOWED (honest frontier, measured on real S5
ticks, train 2024-01..2025-07, OOS 2025-08..2026-06, judged at realistic 0.20/0.30
synthetic spreads in taker mode):

  1. Nested lookbacks are REDUNDANT, not independent. A break of an 80-bar extreme is
     almost always also a break of the 160/240/320-bar extreme at nearly the same bar,
     so unioning {80,160,240,320} yields the SAME distinct trades as {80,240} (~37).
     Multi-scale does NOT multiply opportunities the way the lever hoped.
  2. FINER scales (20/40 bars) DO fire on new sub-leg breaks, but those breaks are
     lower quality; adding them dilutes PF unless gated by a higher per-scale K.
  3. The real within-session multiplier is a retest-depth LADDER: one validated break
     arms several maker limits at increasing retracement depths. This keeps quality
     (every entry shares the same high-displacement break) and improves fill price,
     lifting PF, but the ONE-POSITION engine serializes fills so it adds few trades.
  4. THE EDGE IS A CLIFF, NOT A SLOPE. The displacement gate K*M1-ATR is binary: at
     K>=~1.8 the break carries a real continuation edge (PF ~1.4-1.7 @0.20 taker); the
     instant K drops to ~1.5 the trade count doubles (N 53 -> 102) but PF craters to
     ~0.87. There is no smooth frequency/edge trade-off below the quality gate.
  5. THE EDGE IS SESSION-BOUND. Confined to London+NY hours (07-15 UTC) it holds; add
     Asian/late hours and N triples while PF falls under 1.0. The edge fires on only
     ~40 of ~230 OOS trading days -> ~1 trade/active-day is the natural frequency.

RESULT OF THIS CANDIDATE (5 scales, 3-depth ladder, fast 15-min bias, London+NY):
  OOS ~50 trades at PF ~1.43 @0.25 taker, ~1.25 @0.30 taker (positive). This is the
  honest CEILING of the multi-scale lever while HOLDING the edge. The >=100-trade /
  3-25-per-day target is NOT reachable with this edge: every route to 100+ trades
  (looser K, more hours, finer noisy scales) crosses the quality cliff and the edge
  dies. Frequency is a wall on XAU 5s micro-BOS; ~50 high-quality OOS trades at a real
  PF is the deliverable, reported with the frontier that proves the wall.

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only (info up to bar i close).
NO LOOK-AHEAD: roll_max/min causal (exclude current bar); M1-ATR aligned to the last
completed M1 bar; EMA causal.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_multiscale_r3"

SIM = dict(maxhold=480, dollars_per_point=1.0, commission=0.07, cooldown=5,
           trail_pts=4.0, be_at_pts=0.0)

# --- multi-scale structure: (lookback S5 bars, per-scale displacement K) ---
# Finer 40-bar scale demands a larger K (2.4) to stay above the quality cliff;
# the 80..320 scales use the proven K=1.8.
SCALE_K = ((40, 2.4), (80, 1.8), (160, 1.8), (240, 1.8), (320, 1.8))
DEPTHS  = (0.20, 0.45, 0.70)   # retest-depth ladder: maker limits per validated break
RETR_REF = None
SL_PTS  = 5.0                  # structure-wide stop from fill
TTL     = 170                  # bars the retest limits stay live (~14 min)
ATR_LO  = 0.16                 # skip dead tape  (M1 ATR pts)
ATR_HI  = 1.80                 # skip runaway tape (M1 ATR pts)
BIAS_EMA = 900                 # fast S5 EMA for trend bias (~15 min) -- beats the 5h EMA
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active (UTC)


def _m1_atr_aligned(b: Bars):
    """Wilder ATR on M1 mid bars, aligned to S5 by the LAST COMPLETED M1 bar (causal)."""
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


def _scale_breaks(mid, A1, thr, sess, volok, bias_up, bias_dn, lookback):
    """Fresh-edge micro-BOS break indices + displacement size at one lookback."""
    rmax = roll_max(mid, lookback)
    rmin = roll_min(mid, lookback)
    disp_up = mid - rmax          # >0 when broken above
    disp_dn = rmin - mid          # >0 when broken below
    brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
    brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn
    fu = brk_up.copy(); fu[1:] &= ~brk_up[:-1]
    fd = brk_dn.copy(); fd[1:] &= ~brk_dn[:-1]
    return np.where(fu)[0], disp_up, np.where(fd)[0], disp_dn


def generate(b: Bars) -> Signals:
    mid = b.mid
    A1 = _m1_atr_aligned(b)
    Eb = ema(mid, BIAS_EMA)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    bias_up = mid > Eb
    bias_dn = mid < Eb

    I, SD, LV = [], [], []
    for lb, K in SCALE_K:
        thr = K * A1
        iu, disp_up, il, disp_dn = _scale_breaks(mid, A1, thr, sess, volok,
                                                  bias_up, bias_dn, lb)
        for dep in DEPTHS:
            # continuation longs: buy-limit dip into the up-displacement leg
            I.append(iu); SD.append(np.ones(len(iu), int))
            LV.append(mid[iu] - dep * disp_up[iu])
            # continuation shorts: sell-limit pop into the down-displacement leg
            I.append(il); SD.append(-np.ones(len(il), int))
            LV.append(mid[il] + dep * disp_dn[il])

    i = np.concatenate(I)
    side = np.concatenate(SD)
    level = np.concatenate(LV)
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(n, int),                # LIMIT maker entry at the retest
        level=level,
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, np.inf),           # trail-only (SIM.trail_pts rides the leg)
        ttl=np.full(n, TTL, np.int64),
    )
