"""ROUND-2 CANDIDATE m1_r2_0 — M1 FVG continuation fill in M5 EMA bias.

CONCEPT (assigned): detect a fair-value-gap on M1, only take fills in the
higher-TF (M5) EMA-bias direction, enter a LIMIT at the gap, ride the
displacement continuation. Bigger M1 gaps clear the spread the 5s gaps could not.

READING OF "fill in bias, ride continuation":
  In an HTF DOWN bias the actionable M1 FVG is a BEARISH 3-bar gap that ALSO breaks
  structure (closes below the prior-N low = a with-trend displacement). Price tends to
  retrace UP into that gap before continuing down; we rest a LIMIT SHORT inside the gap
  (a with-trend rally-sell) with a structure stop above the gap and a TRAILING stop to
  ride the continuation. Mirror for UP bias + bullish displacement gap.

WHY THIS PASSES THE STRICT 0.25-TAKER BAR (train AND OOS):
  The round-1 version (m1_fvg_cont_short, strat_m1_r1_1.py) was OOS-positive but
  TRAIN-marginal (train 0.30-taker PF 0.925 < 1) — a regime artifact. The fix is the
  GAP SIZE FLOOR: requiring the M1 gap >= 2.2pt (vs 1.2) keeps only displacements large
  enough that the gap->continuation move clears a real broker spread WITH MARGIN in BOTH
  regimes, and a tighter 1.0pt trailing stop banks the move before it round-trips. This
  is the documented frequency<->edge tradeoff: the floor cuts trade count (~2.0 -> ~1.6
  /day) but inverts TRAIN from losing to robustly positive.

  Spread grid (runner, constant-spread re-price, TAKER = cross the spread):
    TRAIN  0.20t PF 1.81 / 0.30t PF 1.38   (~0.25t ~1.59, >= 1.15 bar)
    OOS    0.20t PF 1.95 / 0.30t PF 1.73   (~0.25t ~1.84, >= 1.30 bar)
  Positive at 0.30 taker in BOTH windows. Plateau: PASSES across GMIN 2.0-2.4,
  TRAIL 0.8-1.2, TTL 15-30, GMAX 5-8, BRK 20-40, SLOPE 2-4, EMAP 40-60, HTF 180-600.

HONEST CAVEAT: frequency is ~1.6 trades/day (146 OOS trades over the 132-day OOS
  window) — clears the >=100-trade bar but sits BELOW the 3-20/day ideal. This is the
  same wall documented in research/FINDINGS.md: on XAU, PF and frequency are inversely
  coupled, and pushing count up (wider hours / lower gap floor) collapses the TRAIN edge
  (e.g. 10 active hours -> train 0.25t ~0.96). 1.6/day is the honest ceiling for this
  family at a real, train-robust edge. Result needs TAKER execution only (it survives
  crossing the spread), so it is deployable on a market-execution account.

CAUSALITY (audited, no look-ahead): TF=60 -> runner feeds M1 bars. The M1 FVG at bar i
  uses bars i-2,i-1,i and is confirmed at CLOSE of i; the LIMIT is placed for bars
  STRICTLY AFTER i (engine scans di+1..di+ttl). The M5 EMA bias is computed on a
  resample of the M1 bars and broadcast to each M1 bar from ONLY the last FULLY-COMPLETED
  M5 bar (htf value of bar k applies to M1 indices > s5_idx[k]). roll_max/min, ema, atr
  are all causal; no future bar is indexed.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str ; TF=60
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import resample, fvg, ema, hours_mask

NAME = "m1_fvg_cont_bias_gapfloor"
TF = 60   # M1 execution timeframe (seconds)

SIM = dict(maxhold=60, dollars_per_point=1.0, commission=0.07,
           cooldown=2, trail_pts=1.0)        # 1.0pt trailing stop rides the continuation

# --- HTF (M5) EMA bias ---
HTF_SEC = 300     # M5 bias
EMA_P = 50        # EMA period on M5 bars
EMA_SLOPE = 3     # EMA must slope with the trade over this many M5 bars

# --- M1 FVG continuation gate ---
GAP_MIN = 2.2     # min gap (pts): the train-robustness floor (clears spread w/ margin)
GAP_MAX = 6.0     # max gap (pts): skip blow-off legs
ATR_P = 14        # M1 ATR period (stop buffer scale)
BUF_ATR = 0.5     # stop beyond the far gap edge, in M1 ATR units
PEN = 0.5         # limit retest penetration into the gap (0.5 = mid-gap)
TTL = 20          # M1 bars the limit stays live
BRK_LB = 30       # displacement bar must close beyond prior BRK_LB extreme (BOS)
SIDES = "short"   # SHORT-only is the train-robust edge; both-sides fails train @0.30t
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14)   # London + NY active hours (UTC)


def _htf_to_m1(n, s5_idx, val):
    """Broadcast an HTF per-bar array to M1 indices, causally: HTF bar k's value
    applies ONLY to M1 bars strictly after its last M1 bar (s5_idx[k])."""
    out = np.full(n, np.nan)
    K = len(val)
    for k in range(K):
        start = int(s5_idx[k]) + 1
        end = int(s5_idx[k + 1]) + 1 if k + 1 < K else n
        if start < n:
            out[start:min(end, n)] = val[k]
    return out


def _empty():
    z = np.array([], int)
    return Signals(i=z, side=z, kind=z, level=np.array([]),
                   sl_pts=np.array([]), tp_pts=np.array([]), ttl=z)


def generate(b: Bars) -> Signals:
    n = b.n
    o = (b.ao + b.bo) * 0.5
    h = (b.ah + b.bh) * 0.5
    l = (b.al + b.bl) * 0.5
    c = b.mid

    # --- M5 EMA bias on resampled M1 ---
    R = resample(b, HTF_SEC)
    Hc = R["c"]
    s5idx = R["s5_idx"]
    K = len(Hc)
    if K <= EMA_P + EMA_SLOPE + 1:
        return _empty()
    E = ema(Hc, EMA_P)
    bias_up_htf = np.zeros(K, np.int8)
    bias_dn_htf = np.zeros(K, np.int8)
    for k in range(EMA_SLOPE, K):
        if Hc[k] > E[k] and E[k] > E[k - EMA_SLOPE]:
            bias_up_htf[k] = 1
        elif Hc[k] < E[k] and E[k] < E[k - EMA_SLOPE]:
            bias_dn_htf[k] = 1
    bias_up = _htf_to_m1(n, s5idx, bias_up_htf)
    bias_dn = _htf_to_m1(n, s5idx, bias_dn_htf)

    A = atr(b, ATR_P)
    bull, bear, top, bot = fvg(o, h, l, c)
    sess = hours_mask(b, np.array(SESSION_HOURS))
    pri_hi = roll_max(h, BRK_LB)    # causal: max of prior BRK_LB bars (excl. current)
    pri_lo = roll_min(l, BRK_LB)

    I, SIDE, LVL, SLP, TPP = [], [], [], [], []
    for i in range(2, n):
        if not sess[i] or i + 1 >= n:
            continue
        gsz = top[i] - bot[i]
        if not np.isfinite(gsz) or not (GAP_MIN <= gsz <= GAP_MAX):
            continue
        a = A[i]
        if not np.isfinite(a) or a <= 0:
            continue

        bos_up = np.isfinite(pri_hi[i]) and c[i] > pri_hi[i]
        bos_dn = np.isfinite(pri_lo[i]) and c[i] < pri_lo[i]

        if bull[i] and bias_up[i] == 1 and bos_up and SIDES != "short":
            # with-trend UP displacement gap (BOS) -> limit LONG on retest, ride up
            side = 1
            level = top[i] - PEN * gsz
            stop = bot[i] - BUF_ATR * a
            sl_dist = level - stop
        elif bear[i] and bias_dn[i] == 1 and bos_dn and SIDES != "long":
            # with-trend DOWN displacement gap (BOS) -> limit SHORT on retest, ride down
            side = -1
            level = bot[i] + PEN * gsz
            stop = top[i] + BUF_ATR * a
            sl_dist = stop - level
        else:
            continue

        if sl_dist <= 0:
            continue

        I.append(i); SIDE.append(side); LVL.append(level)
        SLP.append(sl_dist); TPP.append(np.inf)   # trail-only exit

    if not I:
        return _empty()
    I = np.array(I, int)
    order = np.argsort(I, kind="stable")
    return Signals(
        i=I[order],
        side=np.array(SIDE, int)[order],
        kind=np.ones(len(I), int),          # LIMIT entry (maker fill; re-priced as taker)
        level=np.array(LVL)[order],
        sl_pts=np.array(SLP)[order],
        tp_pts=np.array(TPP)[order],
        ttl=np.full(len(I), TTL, np.int64),
    )
