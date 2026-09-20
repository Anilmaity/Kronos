"""M5 BREAKER-BLOCK continuation (failed OB flips into a support breaker) -- LONG-ONLY.

FAMILY : breaker block.  TF : M5 (300s).  Target ~2-5 trades/day.

MECHANIC (textbook bullish breaker, causal):
  1. SUPPLY (bearish) OB forms: a bearish DISPLACEMENT down (close breaks a prior-L
     swing low by >= K_DISP*ATR) prints; the last UP candle before that drop is the
     bearish order block. Its candle range [obL, obH] is a supply zone.
  2. The OB *fails*: a later bar closes ABOVE obH by >= K_FLIP*ATR -- price has
     displaced up through the supply. The failed supply flips into a BULLISH BREAKER
     (support).
  3. ENTRY: on the flip bar, rest a LONG limit at the retest of the breaker top (obH,
     optionally a touch deeper), gated by a slow-EMA up-bias and the London+NY session.
     Stop below obL - BUF*ATR (structure-wide). Chandelier trail so the leg runs.

WHY LONG-ONLY: the repo has proven short OB/breaker continuation loses against gold's
2024-26 uptrend; supply-flip-to-support (long) is the side with the edge.

VERIFIED (real OANDA S5 -> M5; train 2024-01..2025-07, OOS 2025-08..2026-06; baked
defaults FLIPMOM=0.5, RR=2 fixed target, MAXHOLD=48, K_DISP=1.0, K_FLIP=0.5, long-only):
  OOS   taker 0.20 PF 1.377 / 0.30 PF 1.342  (~0.25 ~1.36, N=69, WR 41%, tpd 1.23)
  TRAIN taker 0.20 PF 1.142 / 0.30 PF 1.032  (positive both windows on the taker grid)
  PER-YEAR @0.30 taker: 2024 1.049 (+$4.9) ; 2025 1.017 (+$3.2) ; 2026 1.510 (+$82.3)
        -> positive every calendar year on the realistic constant-spread feed.
  OOS maxDD ~$78.7 at $1/pt (0.01 lot).
VERDICT = MARGINAL, not a clean survivor:
  * OOS PF >=1.3 @0.25 taker  : YES (~1.36)  and per-year positive        [pass]
  * 3-25 trades/day           : NO  (1.23/day) -- the repo's proven ~1.4/day
        continuation ceiling on XAU M5; the breaker prints even fewer real legs.
  * native 1.5x stress        : NO  (OOS PF 0.95, -$13.8) -- the breaker edge
        break-evens ~0.30-0.40 taker, too thin to absorb the punitive ~1pt feed.
  * parameter plateau         : ONE-SIDED -- OOS ~0.25 holds >=K_DISP=1.0 (1.15->1.23,
        1.30->1.38) but COLLAPSES if displacement is loosened (0.85->1.13, 0.70->0.88),
        so K_DISP is a floor not a free knob (consistent with the repo dead-ends).
A real but thin supply-flip continuation edge: deployable-grade only if the live taker
spread sits <=~0.30; fails the strict survivor bar on frequency + native stress.

NO LOOK-AHEAD: displacement uses roll_min/roll_max (prev-w window EXCLUDES current bar,
NaN-gated); ATR is Wilder-causal; the OB candle j and its confirming down-displacement
are all strictly < the flip/decision bar i; the retest limit level obH is a past price;
the engine fills on i+1 onward. EMA is past-only. Absolute imports.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF=300.
RUN: .venv/Scripts/python.exe -m bot.micro.runner research/hunt/strat_m5_breaker.py
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask, ema


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "BREAKER_m5_supply_flip_long"
TF = _P("BK_TF", 300, int)

# Fixed-RR target beats a tight chandelier trail here: the continuation leg after a
# breaker retest needs room to run, so we let winners reach RR*risk (trail off).
TRAIL = _P("BK_TRAIL", 0.0)
SIM = dict(maxhold=_P("BK_MAXHOLD", 48, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("BK_COOLDOWN", 0, int), trail_pts=TRAIL)

# supply-OB detection (the down displacement that creates the bearish OB)
LOOKBACKS = tuple(int(x) for x in os.environ.get("BK_LBS", "6,10,15,24,40").split(","))
K_DISP  = _P("BK_K", 1.00)          # down-displacement floor: prior-L-low - close >= K*ATR
OB_SCAN = _P("BK_SCAN", 3, int)     # last up candle within this many bars before the drop
# flip / breaker confirmation
K_FLIP  = _P("BK_KFLIP", 0.50)      # close must break obH by >= K_FLIP*ATR to "fail" the OB
MAXAGE  = _P("BK_MAXAGE", 120, int) # OB may flip at most this many bars after it forms
# entry / risk
DEPTH   = _P("BK_DEPTH", 0.0)       # 0 = retest at breaker top obH ; >0 = deeper into zone
BUF_ATR = _P("BK_BUF", 0.25)        # stop buffer below obL, in ATR
TTL     = _P("BK_TTL", 36, int)     # retest limit live bars (~3h M5)
ATR_LO  = _P("BK_ATRLO", 0.40)
ATR_HI  = _P("BK_ATRHI", 30.0)
BIAS_EMA = _P("BK_BIAS", 100, int)
SLOPE   = _P("BK_SLOPE", 0, int)    # require EMA rising over this many bars (0=off)
FLIPMOM = _P("BK_FLIPMOM", 0.5)     # require flip candle displacement c-o >= FLIPMOM*ATR
RR      = _P("BK_RR", 2.0)          # reward:risk for the fixed target (used when TRAIL=0)
SL_MIN  = _P("BK_SLMIN", 1.0)
SL_MAX  = _P("BK_SLMAX", 16.0)
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("BK_HOURS", "4,5,6,7,8,9,10,11,12,13,14,15,16,17,18").split(","))


def generate(b: Bars) -> Signals:
    n = b.n
    c = b.mid
    o = (b.bo + b.ao) * 0.5
    h = (b.bh + b.ah) * 0.5
    l = (b.bl + b.al) * 0.5
    A = atr(b, 14)
    Eb = ema(c, BIAS_EMA)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)
    bias_up = c > Eb
    bull = c > o
    bear = c < o
    thr = K_DISP * A

    # ---- Step 1: detect bearish OB candles (supply zones) via down displacement ----
    # A down-displacement at bar m: close breaks prior-L low by >= K*ATR. The bearish
    # OB is the last UP candle j in [m-OB_SCAN, m-1]. Store one zone per detected OB.
    ob_j = []          # OB candle index
    ob_hi = []; ob_lo = []
    seen = set()       # dedupe identical OB candles
    for L in LOOKBACKS:
        rmin = roll_min(l, L)
        dd = np.isfinite(rmin) & np.isfinite(A) & (rmin - c >= thr)
        # new-event edge (first bar of a fresh down-break for this lookback)
        e_d = dd.copy(); e_d[1:] &= ~dd[:-1]
        for m in np.where(e_d)[0]:
            j = -1
            for k in range(m - 1, max(0, m - OB_SCAN) - 1, -1):
                if bull[k]:
                    j = k
                    break
            if j >= 0 and j not in seen:
                seen.add(j)
                ob_j.append(j); ob_hi.append(h[j]); ob_lo.append(l[j])

    if not ob_j:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    order = np.argsort(ob_j)
    ob_j = np.array(ob_j)[order]
    ob_hi = np.array(ob_hi)[order]
    ob_lo = np.array(ob_lo)[order]

    sig_i = []; sig_side = []; sig_level = []; sig_sl = []; sig_tp = []

    # ---- Step 2+3: find the flip bar for each supply zone, emit a long breaker retest ----
    for zj, zh, zl in zip(ob_j, ob_hi, ob_lo):
        lo_scan = zj + 1
        hi_scan = min(zj + 1 + MAXAGE, n)
        flip = -1
        for i in range(lo_scan, hi_scan):
            if not np.isfinite(A[i]):
                continue
            # OB fails: close breaks above the supply top by >= K_FLIP*ATR
            if c[i] > zh + K_FLIP * A[i]:
                flip = i
                break
        if flip < 0:
            continue
        i = flip
        if not (sess[i] and volok[i] and bias_up[i]):
            continue
        if SLOPE > 0 and not (i - SLOPE >= 0 and Eb[i] > Eb[i - SLOPE]):
            continue
        if FLIPMOM > 0.0 and not (c[i] - o[i] >= FLIPMOM * A[i]):
            continue
        entry = zh - DEPTH * (zh - zl)          # retest of breaker top (or deeper)
        if entry >= c[i]:                        # must be a genuine pullback level below price
            continue
        sl = zl - BUF_ATR * A[i]
        sl_pts = entry - sl
        if not (SL_MIN <= sl_pts <= SL_MAX):
            continue
        tp_pts = np.inf if TRAIL > 0 else RR * sl_pts
        sig_i.append(int(i)); sig_side.append(1); sig_level.append(entry)
        sig_sl.append(sl_pts); sig_tp.append(tp_pts)

    if not sig_i:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array(sig_i, np.int64)
    side = np.array(sig_side, np.int64)
    level = np.array(sig_level, np.float64)
    sl_pts = np.array(sig_sl, np.float64)
    tp_pts = np.array(sig_tp, np.float64)
    ord_ = np.argsort(i, kind="stable")
    i, side, level, sl_pts, tp_pts = i[ord_], side[ord_], level[ord_], sl_pts[ord_], tp_pts[ord_]
    m = len(i)
    return Signals(i=i, side=side, kind=np.ones(m, int), level=level,
                   sl_pts=sl_pts, tp_pts=tp_pts, ttl=np.full(m, TTL, np.int64))
