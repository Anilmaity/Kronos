"""CANDIDATE m1_r1_1 — M1 FVG fill in M5/M15 EMA bias, limit entry, origin target.

CONCEPT (assigned): detect a fair-value-gap on M1, only take fills in the
higher-TF EMA-bias direction, enter a LIMIT at the gap, target the displacement
ORIGIN. Bigger M1 gaps clear the spread that the 5s gaps could not.

READING OF "fill in bias, target origin":
  In an HTF UP bias, the actionable M1 FVG is a BEARISH one — a 3-bar DOWN leg, i.e.
  a counter-trend PULLBACK inside the uptrend. Price tends to retrace back UP into and
  through that gap (the gap "fills"). We rest a LIMIT LONG inside the gap (a with-trend
  dip-buy) and target the displacement ORIGIN = the price the down-leg started from
  (the top edge of the gap, l[i-2]). Stop below the gap. Mirror for DOWN bias + bull FVG.

  This is a maker entry (earns spread in maker mode) but the runner ALSO re-prices it as
  a taker (crossing the spread). The bar requires positive @0.25 TAKER in BOTH train+OOS,
  so the gap-to-origin move must be big enough to clear a real broker spread with margin —
  exactly why M1 gaps (median range ~2pt) are used instead of 5s.

CAUSALITY (audited): TF=60 -> the runner hands generate() M1 bars. The M1 FVG at bar i
  uses bars i-2,i-1,i and is confirmed at the CLOSE of bar i; the LIMIT is placed for bars
  STRICTLY AFTER i (engine scans di+1..di+ttl). The HTF (M5/M15) EMA bias is computed on a
  resample of the M1 bars and broadcast to each M1 bar from ONLY the last FULLY-COMPLETED
  HTF bar (htf value of bar k applies to M1 indices > s5_idx[k]). No future bar is indexed;
  roll/EMA/ATR are causal.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str ; TF=60
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import resample, fvg, ema, hours_mask

NAME = "m1_fvg_cont_short"
TF = 60   # M1 execution timeframe (seconds)

def _f(k, d): return float(os.environ.get(k, d))

SIM = dict(maxhold=int(_f("MH", 60)), dollars_per_point=1.0, commission=0.07,
           cooldown=2, trail_pts=_f("TRAIL", 1.5))

# --- HTF bias ---
HTF_SEC = int(_f("HTF", 300))   # M5 bias (900=M15)
EMA_P = int(_f("EMAP", 50))     # EMA period on HTF bars
EMA_SLOPE = int(_f("SLOPE", 3)) # EMA must slope with the trade over this many HTF bars

# --- M1 FVG gate (CONTINUATION: a with-trend displacement gap, retested) ---
GAP_MIN = _f("GMIN", 1.2)       # absolute min gap (pts) to clear the spread floor
GAP_MAX = _f("GMAX", 6.0)       # absolute max gap (pts) - skip blow-off legs
GAP_ATR_MIN = _f("GAMIN", 0.0)  # gap must be >= this * M1 ATR (regime-relative)
GAP_ATR_MAX = _f("GAMAX", 99.0) # gap must be <= this * M1 ATR
ATR_P = 14           # M1 ATR period
BUF_ATR = _f("BUF", 0.5)        # stop beyond the far gap edge, in M1 ATR units
PEN = _f("PEN", 0.5) # limit retest penetration into the gap (0=near edge, 1=far edge)
RR = _f("RR", 0.0)   # fixed target = RR * risk; RR<=0 -> trail-only (np.inf TP)
TTL = int(_f("TTL", 20))   # M1 bars the limit stays live
BRK_LB = int(_f("BRK", 30))  # displacement must close beyond prior BRK-bar extreme (BOS)
SIDES = os.environ.get("SIDES", "short")  # both / long / short (short = the real edge)
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


def generate(b: Bars) -> Signals:
    n = b.n
    # mid OHLC on M1
    o = (b.ao + b.bo) * 0.5
    h = (b.ah + b.bh) * 0.5
    l = (b.al + b.bl) * 0.5
    c = b.mid

    # --- HTF bias on resampled M1 ---
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
    pri_hi = roll_max(h, BRK_LB)   # causal: max of prior BRK_LB bars (excl. current)
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
        if not (GAP_ATR_MIN * a <= gsz <= GAP_ATR_MAX * a):
            continue

        # BOS gate: the displacement bar must close beyond the prior-N extreme
        bos_up = np.isfinite(pri_hi[i]) and c[i] > pri_hi[i]
        bos_dn = np.isfinite(pri_lo[i]) and c[i] < pri_lo[i]

        if bull[i] and bias_up[i] == 1 and bos_up and SIDES != "short":
            # with-trend UP displacement gap (BOS) -> limit LONG on the retest into it,
            # ride the continuation up (target above + trailing stop)
            side = 1
            level = top[i] - PEN * gsz            # retest down into the gap
            stop = bot[i] - BUF_ATR * a
            sl_dist = level - stop
        elif bear[i] and bias_dn[i] == 1 and bos_dn and SIDES != "long":
            # with-trend DOWN displacement gap (BOS) -> limit SHORT on the retest into it
            side = -1
            level = bot[i] + PEN * gsz
            stop = top[i] + BUF_ATR * a
            sl_dist = stop - level
        else:
            continue

        if sl_dist <= 0:
            continue
        tp_dist = RR * sl_dist if RR > 0 else np.inf

        I.append(i); SIDE.append(side); LVL.append(level)
        SLP.append(sl_dist); TPP.append(tp_dist)

    if not I:
        return _empty()
    I = np.array(I, int)
    order = np.argsort(I, kind="stable")
    return Signals(
        i=I[order],
        side=np.array(SIDE, int)[order],
        kind=np.ones(len(I), int),          # LIMIT entry
        level=np.array(LVL)[order],
        sl_pts=np.array(SLP)[order],
        tp_pts=np.array(TPP)[order],
        ttl=np.full(len(I), TTL, np.int64),
    )


def _empty():
    z = np.array([], int)
    return Signals(i=z, side=z, kind=z, level=np.array([]),
                   sl_pts=np.array([]), tp_pts=np.array([]), ttl=z)
