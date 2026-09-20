"""Micro-BOS continuation: displacement break -> shallow retrace -> retest entry.

ASSIGNED CONCEPT
  A displacement break of micro-structure (close beyond the prior N-bar extreme by
  > K_ATR*ATR) followed by a SHALLOW retrace; enter the CONTINUATION on the retest,
  not on the breakout.

PRECISE RULES (all causal -- only info up to bar i's close is used)
  1. rmax/rmin = causal rolling extreme over LOOKBACK bars (excludes current bar).
  2. Fresh displacement break UP at bar i:  mid[i] > rmax[i] + K_ATR*ATR[i], in an
     active session, with ATR in [ATR_LO, ATR_HI], and micro-bias up (mid > EMA).
     "Fresh" = the bar before was not already broken (dedupes a long run of highs).
  3. From the break bar, scan forward up to W bars for the retest pattern:
       - price must PULL BACK at least MINPULL*ATR below the break high (a retrace),
       - the retrace must stay SHALLOW (<= MAXPULL*ATR) and hold above the broken
         level minus BUF_PTS (structure intact),
       - then RESUME: a bar prints a new high above the break high -> enter long
         (market, next-bar open). This confirmation is what avoids the adverse
         selection of a passive limit (which only fills the retraces that fail).
  4. Stop sits just beyond the broken level (structure invalidation), floored at
     MIN_SL so a sub-spread stop is never used. Target = R_MULT * stop.
  Shorts are the mirror image.

WHY MARKET (TAKER) ENTRY
  This is the deployable execution mode for the user's FundingPips MT5 account.
  A maker-limit retest was tested and is worse here: it systematically misses the
  straight-line continuations (they never trade back to the level) and only fills
  the weak retraces that then fail.

HONEST RESULT (see runner output): this concept has NO live-tradeable edge on XAU
  5-second bars. Across continuation, the fade (flipped side), and maker/taker
  execution, win rate clusters at ~20-30% for takers and profit factor never
  exceeds ~0.76 even for maker wide-stop/trailing variants -- a fresh micro-extreme
  entry is whipsawed by noise (spread 0.66pt vs 0.26pt bar range) regardless of
  direction. Reported as a negative result with evidence, per GOAL.md.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask, ema

NAME = "micro_bos_cont"

SIM = dict(maxhold=240, dollars_per_point=1.0, commission=0.07, cooldown=20)

# --- tunable params (runner sweeps these +-30%) ---
LOOKBACK = 120        # bars defining the micro extreme that gets broken
K_ATR    = 1.2        # break must clear the extreme by this * ATR (displacement)
W        = 60         # bars allowed for the retrace+resumption to complete
MINPULL  = 0.3        # retrace must be at least this * ATR (a real pullback)
MAXPULL  = 1.2        # ...but no deeper than this * ATR (stay shallow)
BUF_PTS  = 0.5        # structure-invalidation buffer beyond the broken level
MIN_SL   = 1.5        # floor on stop distance (must exceed spread noise)
R_MULT   = 2.0        # target = R_MULT * stop distance
ATR_LO, ATR_HI = 0.30, 1.60
SLOPE_EMA = 600       # micro-bias EMA period (bars)
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15, 16)   # London + NY (UTC)


def generate(b: Bars) -> Signals:
    A = atr(b, 14)
    mid = b.mid
    ts = b.ts
    rmax = roll_max(mid, LOOKBACK)
    rmin = roll_min(mid, LOOKBACK)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)
    e = ema(mid, SLOPE_EMA)
    up_bias = mid > e
    dn_bias = mid < e

    brk_up = (mid > rmax + K_ATR * A) & np.isfinite(rmax) & sess & volok & up_bias
    brk_dn = (mid < rmin - K_ATR * A) & np.isfinite(rmin) & sess & volok & dn_bias
    fresh_up = brk_up.copy(); fresh_up[1:] &= ~brk_up[:-1]
    fresh_dn = brk_dn.copy(); fresh_dn[1:] &= ~brk_dn[:-1]
    iu = np.where(fresh_up)[0]
    il = np.where(fresh_dn)[0]

    I = []; S = []; SL = []; TP = []
    n = b.n

    # longs: break up -> shallow pullback that holds -> new high (resumption)
    for i in iu:
        pbh = mid[i]; invalid = rmax[i] - BUF_PTS
        minp = MINPULL * A[i]; maxp = MAXPULL * A[i]
        pulled = False; lo = pbh
        jmax = min(i + 1 + W, n); j = i + 1
        while j < jmax:
            if ts[j] - ts[j - 1] > 30:
                break
            m = mid[j]
            if m < invalid:
                break                      # structure broken -> abort
            if m < lo:
                lo = m
            depth = pbh - lo
            if not pulled and depth >= minp:
                pulled = True
            if pulled:
                if depth > maxp:
                    break                  # pullback too deep -> abort
                if m > pbh:                # resumption: new high
                    sl = max(pbh - invalid, MIN_SL)
                    I.append(j); S.append(1); SL.append(sl); TP.append(R_MULT * sl)
                    break
            j += 1

    # shorts: mirror image
    for i in il:
        pbl = mid[i]; invalid = rmin[i] + BUF_PTS
        minp = MINPULL * A[i]; maxp = MAXPULL * A[i]
        pulled = False; hi = pbl
        jmax = min(i + 1 + W, n); j = i + 1
        while j < jmax:
            if ts[j] - ts[j - 1] > 30:
                break
            m = mid[j]
            if m > invalid:
                break
            if m > hi:
                hi = m
            depth = hi - pbl
            if not pulled and depth >= minp:
                pulled = True
            if pulled:
                if depth > maxp:
                    break
                if m < pbl:
                    sl = max(invalid - pbl, MIN_SL)
                    I.append(j); S.append(-1); SL.append(sl); TP.append(R_MULT * sl)
                    break
            j += 1

    I = np.array(I, int)
    o = np.argsort(I, kind="stable")
    k = len(I)
    return Signals(
        i=I[o], side=np.array(S, int)[o],
        kind=np.zeros(k, int),                 # market entry next bar (taker)
        level=np.zeros(k),
        sl_pts=np.array(SL, float)[o],
        tp_pts=np.array(TP, float)[o],
    )
