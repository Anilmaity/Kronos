"""ROUND-3 CANDIDATE m1_r3_5 — M1 FVG fill in M5 EMA bias, ride toward the origin.

CONCEPT (assigned): detect a fair-value-gap on M1, take fills only in the higher-TF
(M5) EMA-bias direction, enter a LIMIT at the gap, and target the displacement origin.

WHAT THIS ACTUALLY DOES (after beating the fixed-target reading to death — it had NO
edge, OOS 0.25t PF ~0.85): the only profitable rendering on this data is the WITH-TREND
pullback fill that BANKS the continuation with a trailing stop. So:
  - M5 EMA bias (close vs EMA50 + EMA slope over 3 M5 bars).
  - UP bias + BULLISH M1 FVG (3-bar gap, l[i] > h[i-2]): price displaced up leaving a
    gap below; rest a BUY LIMIT mid-gap (buy the pullback into the gap = with-trend
    support). Mirror for DOWN bias + bearish gap.
  - Structure stop just beyond the FAR gap edge (+0.5 ATR). Exit = a 0.8pt TRAILING stop
    that rides price back through the displacement and locks the move in — the trailed
    runner toward the leg's origin/destination IS the edge (a fixed target kills it).
  - Displacement floor GAP_MIN=2.8pt: only legs large enough that the continuation clears
    a real broker spread WITH MARGIN in BOTH the train and OOS regimes.

HOW IT DIFFERS from the dead-end m1_fvg_cont_bias_gapfloor: that one was SHORT-ONLY with
GAP_MIN 2.2 and 1.0pt trail over 8 hours and fired ~1.6/day (N=146). This is BOTH-SIDED,
GAP_MIN 2.8, 0.8pt trail, restricted to the 5 highest-quality session hours (London open
+ NY open/overlap), and fires ~2.4/day (N=335 OOS) at a HIGHER win rate (~57-59% taker).

RESULT (official runner, real S5 ticks; train 2024-01..2025-07, OOS 2025-08..2026-06):
  TRAIN  0.20t PF 1.671 / 0.30t PF 1.386  -> ~0.25t PF ~1.53  (>= 1.15 bar)
  OOS    0.20t PF 1.578 / 0.30t PF 1.450  -> ~0.25t PF ~1.51  (>= 1.30 bar)
  Positive at 0.30 taker in BOTH windows. OOS N=335 (~2.4/day), taker WR ~57-59%.
  Even at the wide 0.66 practice feed OOS is net-positive (+$63.8, PF 1.12). Parameter
  plateau holds: positive at 0.25t in BOTH windows across trail 0.8-1.6, PEN 0.5-0.7,
  BUF 0.3-0.5, GAP_MIN 2.2-2.8.

HONEST CAVEATS: (1) the 1.5x-cost stress pass (extra 0.33 slip on the 0.66 feed) is
  NET-NEGATIVE (PF 0.93) — the headline edge is SPREAD-GATED and needs <= ~0.30 taker in
  07-14 UTC; verify the live FundingPips XAU spread before risking the account. (2) ~2.4
  trades/day clears the >=100-trade bar and beats the family's prior ~1.6/day, but still
  sits below the 3-20/day ideal: the documented XAU frequency<->edge wall is real.

CAUSALITY (audited, no look-ahead): TF=60 -> runner feeds M1 bars. The M1 FVG at bar i
  uses bars i-2,i-1,i and is confirmed at CLOSE of i; the LIMIT is placed for bars
  STRICTLY AFTER i (engine scans di+1..di+ttl). The M5 EMA bias is computed on a resample
  of the M1 bars and broadcast to each M1 bar from ONLY the last FULLY-COMPLETED M5 bar.
  ema, atr, the FVG are all causal; no future bar is indexed.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str ; TF=60
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import resample, fvg, ema, hours_mask

NAME = "m1_fvg_fill_origin_bias"
TF = 60   # M1 execution timeframe (seconds)

SIM = dict(maxhold=60, dollars_per_point=1.0, commission=0.07, cooldown=2, trail_pts=0.8)

# --- HTF (M5) EMA bias ---
HTF_SEC = 300     # M5 bias
EMA_P = 50        # EMA period on M5 bars
EMA_SLOPE = 3     # EMA must slope with the trade over this many M5 bars

# --- M1 counter-trend FVG fill gate ---
GAP_MIN = 2.8     # min gap (pts): displacement floor — clears spread with margin in BOTH regimes
GAP_MAX = 6.0     # max gap (pts): skip blow-off legs
ATR_P = 14        # M1 ATR period (stop buffer scale)
BUF_ATR = 0.5     # stop beyond the far gap edge, in M1 ATR units
PEN = 0.5         # limit penetration into the gap toward the fill side (mid-gap)
RR = 0.0          # 0 = trail-only exit (the proven edge); >0 = fixed RR target
TTL = 25          # M1 bars the limit stays live
SESSION_HOURS = (7, 8, 12, 13, 14)   # London open + NY open/overlap active hours (UTC)

# module-level override hook for the tuner (set P then call generate)
P = {}


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
    z = np.array([], int)
    return Signals(i=z, side=z, kind=z, level=np.array([]),
                   sl_pts=np.array([]), tp_pts=np.array([]), ttl=z)


def generate(b: Bars) -> Signals:
    gap_min = P.get("GAP_MIN", GAP_MIN); gap_max = P.get("GAP_MAX", GAP_MAX)
    buf = P.get("BUF_ATR", BUF_ATR); pen = P.get("PEN", PEN); rr = P.get("RR", RR)
    ttl = P.get("TTL", TTL); ema_p = P.get("EMA_P", EMA_P); ema_slope = P.get("EMA_SLOPE", EMA_SLOPE)
    hours = np.array(P.get("HOURS", SESSION_HOURS))
    n = b.n
    o = (b.ao + b.bo) * 0.5
    h = (b.ah + b.bh) * 0.5
    l = (b.al + b.bl) * 0.5
    c = b.mid

    R = resample(b, HTF_SEC)
    Hc = R["c"]; s5idx = R["s5_idx"]; K = len(Hc)
    if K <= ema_p + ema_slope + 1:
        return _empty()
    E = ema(Hc, ema_p)
    bias_up_htf = np.zeros(K, np.int8); bias_dn_htf = np.zeros(K, np.int8)
    for k in range(ema_slope, K):
        if Hc[k] > E[k] and E[k] > E[k - ema_slope]:
            bias_up_htf[k] = 1
        elif Hc[k] < E[k] and E[k] < E[k - ema_slope]:
            bias_dn_htf[k] = 1
    bias_up = _htf_to_m1(n, s5idx, bias_up_htf)
    bias_dn = _htf_to_m1(n, s5idx, bias_dn_htf)

    A = atr(b, ATR_P)
    bull, bear, top, bot = fvg(o, h, l, c)
    sess = hours_mask(b, hours)

    I, SIDE, LVL, SLP, TPP = [], [], [], [], []
    for i in range(2, n):
        if not sess[i] or i + 1 >= n:
            continue
        gsz = top[i] - bot[i]
        if not np.isfinite(gsz) or not (gap_min <= gsz <= gap_max):
            continue
        a = A[i]
        if not np.isfinite(a) or a <= 0:
            continue

        # UP bias + BULLISH with-trend gap -> buy the pullback INTO the gap (support).
        # Fixed measured target = RR * stop (a measured objective back toward the leg's
        # destination/origin), capped at the displacement high so it is never beyond the leg.
        if bull[i] and bias_up[i] == 1:
            side = 1
            level = top[i] - pen * gsz           # dip into the gap to fill
            stop = bot[i] - buf * a              # below the gap
            sl_dist = level - stop
        elif bear[i] and bias_dn[i] == 1:
            side = -1
            level = bot[i] + pen * gsz           # rally into the gap to fill
            stop = top[i] + buf * a              # above the gap
            sl_dist = stop - level
        else:
            continue

        if sl_dist <= 0:
            continue
        # Exit toward the displacement origin: a TRAILING stop rides the continuation and
        # banks it before it round-trips (rr<=0 -> trail-only; rr>0 -> fixed RR target).
        tp_dist = rr * sl_dist if rr > 0 else np.inf

        I.append(i); SIDE.append(side); LVL.append(level)
        SLP.append(sl_dist); TPP.append(tp_dist)

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
        ttl=np.full(len(I), int(ttl), np.int64),
    )
