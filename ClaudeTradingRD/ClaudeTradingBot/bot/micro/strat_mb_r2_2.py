"""Micro-BOS continuation, RETEST-family frequency push (round 2, candidate 2).

LEVER = entry mechanic (RETEST family). The proven base (strat_r3_1 /
micro_bos_cont_maker) fires ONE shallow-retest maker limit per fresh micro-BOS
break, trend-aligned, ~1 trade/day -> only ~35 OOS trades. The edge is real
(OOS taker PF 1.33@0.20 / 1.10@0.30) but frequency is the wall.

This candidate raises frequency three ways, all inside the proven displacement-
+-retest skeleton, and reports the honest frequency<->PF frontier:

  1. SYMMETRIC bias. The prior `micro_bos_cont_sym` showed dropping the hard
     EMA-bias gate (trade BOTH up- and down-breaks) ~tripled trade count to 97
     while holding PF (t20 1.456 / t30 1.273). We keep a SOFT bias: longs need
     mid>=EMA-slope-down tolerance... actually we keep it fully symmetric but
     require the displacement leg itself to define direction (continuation).

  2. A 2-RUNG RETEST LADDER per break: a shallow retest (RETR1) AND a deeper
     "breaker" retest near the broken level (RETR2). Different pullback depths
     fill on different breaks, so more breaks convert to a trade without
     re-arming on noise. Single-position engine means at most one fills per
     instant; the deeper rung catches breaks whose pullback overshoots the
     shallow level's TTL.

  3. MULTI_LB structure-window union (each window kept at full K_DISP quality)
     and (K_DISP, RETR-depth) tuning, to look for any quality-preserving way to
     multiply break events.

HONEST RESULT — the retest-family frequency lever hits a HARD WALL (this is the
deliverable, not a pass). Measured on real S5 ticks, OOS 2025-08..2026-06, judged
on the runner's constant-spread grid (taker mode):

  The micro-BOS continuation edge is razor-thin and CONCENTRATED in ~1 high-
  displacement break/day during London/NY hours. Every mechanism that raises
  frequency degrades PF monotonically:
    * K_DISP is the edge. K1.8 -> 35 trades pf@.20=1.33/pf@.30=1.10 (~pf.25 1.22).
      K1.6 -> 47 trades but pf@.20 collapses to 0.89. The displacement MAGNITUDE
      is the signal; smaller breaks revert (matches SCOUT note #2).
    * MULTI_LB union (40/80/160 etc.) adds only ~8 trades and the extra breaks are
      lower quality -> pf.25 falls to ~0.94. Wider sessions add Asian-hours breaks
      with NO edge (pf.25 ~0.7). The retest LADDER adds zero trades (single-
      position engine fills only the shallow rung).
    * Deeper "breaker" retest (RETR 0.8-1.2, limit at/below the broken level) makes
      PF WORSE at every K: a pullback that deep means the break is failing, so
      continuation odds drop (pf collapses, WR ~26%). The shallow retest (RETR~0.3-
      0.55) is the only edge-preserving entry depth.
    * The only configs holding pf.25>~1.2 AND pf.30>1.0 sit at 30-35 OOS trades
      (~1/day). The first config that reaches OOS>=100 (K1.2/RETR0.55, 101 trades)
      has pf.25=0.74 -- a clear FAIL.

  CONCLUSION: with the RETEST-family lever there is NO XAU-5s configuration that
  simultaneously clears OOS trades>=100 and PF>=1.3 at 0.25 taker. The frequency
  <->PF frontier is a wall; ~1 trade/day is the edge's natural rate. This module
  is therefore SET to the frontier's max-frequency edge-preserving point (single
  LB80 window, K1.8, shallow RETR0.30, symmetric) -- which reproduces the proven
  base edge (35 OOS grid trades, pf@.20 1.33 / pf@.30 1.10) -- and the knobs above
  document the explored frontier. Consistent with every prior micro_bos dead end
  and the scout's frequency-vs-edge finding. Not a >=100-trade pass; reported for
  the evidence.

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only (info up to bar i close).
"""
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_retest_freqpush"

SIM = dict(maxhold=600, dollars_per_point=1.0, commission=0.07, cooldown=12,
           trail_pts=4.0, be_at_pts=0.0)

# --- tunable params ---
LOOKBACK = 80         # S5 bars defining the micro-structure extreme
K_DISP   = 1.8        # displacement: close beyond extreme by >= K_DISP * M1-ATR
RETR1    = 0.30       # shallow retest depth (limit at mid - RETR1*disp)
RETR2    = 0.62       # deeper "breaker" retest (closer to the broken level)
LADDER   = False      # 2-rung ladder on/off
SL_PTS   = 5.0        # structure-wide stop from fill
TP_PTS   = np.inf     # trail-only exit
TTL      = 90         # bars each retest limit stays live (~7.5 min)
ATR_LO   = 0.20       # skip dead tape  (M1 ATR pts)
ATR_HI   = 1.60       # skip runaway tape (M1 ATR pts)
BIAS_EMA = 3600       # slow S5 EMA (used as a SOFT tolerance, not a hard gate)
BIAS_TOL = 0.0        # 0.0 => fully symmetric (no directional veto)
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active (UTC)


def _m1_atr_aligned(b: Bars):
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


MULTI_LB = (80,)      # structure windows to UNION (each at full K_DISP quality)


def generate(b: Bars) -> Signals:
    mid = b.mid
    A1 = _m1_atr_aligned(b)
    Eb = ema(mid, BIAS_EMA)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    # SOFT bias: with BIAS_TOL=0 these are all True (fully symmetric continuation)
    bias_up = mid >= (Eb - BIAS_TOL)
    bias_dn = mid <= (Eb + BIAS_TOL)
    thr = K_DISP * A1
    finA = np.isfinite(A1)

    iu_i, iu_lvl, il_i, il_lvl = [], [], [], []
    for lb in MULTI_LB:
        rmax = roll_max(mid, lb)
        rmin = roll_min(mid, lb)
        disp_up = mid - rmax
        disp_dn = rmin - mid
        brk_up = np.isfinite(rmax) & finA & (disp_up >= thr) & sess & volok & bias_up
        brk_dn = np.isfinite(rmin) & finA & (disp_dn >= thr) & sess & volok & bias_dn
        fu = brk_up.copy(); fu[1:] &= ~brk_up[:-1]
        fd = brk_dn.copy(); fd[1:] &= ~brk_dn[:-1]
        ju = np.where(fu)[0]; jd = np.where(fd)[0]
        rungs = (RETR1, RETR2) if LADDER else (RETR1,)
        for rr in rungs:
            iu_i.append(ju); iu_lvl.append(mid[ju] - rr * disp_up[ju])
            il_i.append(jd); il_lvl.append(mid[jd] + rr * disp_dn[jd])

    iu_all = np.concatenate(iu_i) if iu_i else np.array([], int)
    il_all = np.concatenate(il_i) if il_i else np.array([], int)
    lvl_u = np.concatenate(iu_lvl) if iu_lvl else np.array([], float)
    lvl_d = np.concatenate(il_lvl) if il_lvl else np.array([], float)

    i = np.concatenate([iu_all, il_all])
    side = np.concatenate([np.ones(len(iu_all), int), -np.ones(len(il_all), int)])
    level = np.concatenate([lvl_u, lvl_d])
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
