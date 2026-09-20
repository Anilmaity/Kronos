"""M1 Opening-Range strategy — London 07:00 + NY 13:30 UTC sessions.

CONCEPT (assigned): opening-range breakout. FINDING (this run): on XAU the
*continuation* break of the opening range has NEGATIVE gross edge (it is the
wrong side — breaks into the London/NY session get faded by liquidity). The
robust, both-window-positive variant of the SAME opening-range machinery is the
FALSE-BREAK FADE: when price pushes decisively beyond the OR after a tight
consolidation, fade it back into the range (the AMD manipulation leg). Entry is
MARKET (taker-compatible), gated by a higher-TF (lagged) trend bias and an
OR-tightness (consolidation) filter; stop a multiple of the OR range, target a
measured move back through the range.

Causality: the OR is built only from bars strictly inside the OR window; signals
fire only AFTER the OR window closes. The trend bias is read from bars lagged
LAG behind the decision bar (independent of the immediate poke). Entry is market
at next-bar open (engine fill). No future bar is indexed.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr

NAME = "m1_or_falsebreak_fade"
TF = 60  # M1 execution timeframe (seconds)

SIM = dict(maxhold=180, dollars_per_point=1.0, commission=0.07, cooldown=0)

# (session_start_minute, OR_minutes, trade_window_end_minute)  [minute-of-day UTC]
SESSIONS = [
    (420, 30, 660),   # London 07:00 OR -> fade 07:30..11:00
    (810, 30, 960),   # NY     13:30 OR -> fade 14:00..16:00
]

BUF_FRAC = 0.05    # decisive-break buffer as a fraction of OR range
SL_K = 1.0         # stop  distance = SL_K * OR range (beyond the poke)
TP_K = 1.0         # target distance = TP_K * OR range (measured move back through range)
MIN_OR = 1.0       # ignore degenerate tiny opening ranges (pts)
LAG = 30           # bars the trend bias trails behind the decision bar (break-independent)
TLB = 240          # trend lookback (M1 bars ~4h) for the lagged bias
ORTIGHT = 8.0      # consolidation filter: OR range must be < ORTIGHT * ATR(14) at OR close


def generate(b: Bars) -> Signals:
    n = b.n
    mid = b.mid
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    minute = b.minute
    day = b.day
    at = atr(b, 14)

    # lagged higher-TF trend bias: direction over the TLB window ending LAG bars ago
    ref = np.full(n, np.nan); ref[LAG:] = mid[:n - LAG]
    sh = np.full(n, np.nan);  sh[LAG + TLB:] = mid[:n - LAG - TLB]
    trend = np.sign(ref - sh)

    I, SIDE, SLP, TPP = [], [], [], []
    for dy in np.unique(day):
        didx = np.where(day == dy)[0]
        if len(didx) == 0:
            continue
        dmin = minute[didx]
        for (start, ormin, tend) in SESSIONS:
            orw = didx[(dmin >= start) & (dmin < start + ormin)]
            if len(orw) < 5:
                continue
            or_hi = hi[orw].max(); or_lo = lo[orw].min()
            orr = or_hi - or_lo
            if orr < MIN_OR:
                continue
            if ORTIGHT > 0 and orr > ORTIGHT * at[orw[-1]]:
                continue  # OR too wide vs ATR -> not a clean consolidation
            buf = BUF_FRAC * orr
            # first decisive break, faded AGAINST it, only if the lagged bias agrees
            for j in didx[(dmin >= start + ormin) & (dmin < tend)]:
                c = mid[j]
                td = trend[j] if np.isfinite(trend[j]) else 0.0
                if c > or_hi + buf and td < 0:          # up-break in a downtrend -> fade short
                    I.append(j); SIDE.append(-1)
                    SLP.append(SL_K * orr); TPP.append(TP_K * orr); break
                if c < or_lo - buf and td > 0:          # down-break in an uptrend -> fade long
                    I.append(j); SIDE.append(1)
                    SLP.append(SL_K * orr); TPP.append(TP_K * orr); break

    if not I:
        e = np.array([], np.float64); ei = np.array([], np.int64)
        return Signals(i=ei, side=ei, kind=ei, level=e, sl_pts=e, tp_pts=e, ttl=ei)
    I = np.array(I, np.int64)
    o = np.argsort(I, kind="stable")
    I = I[o]
    SIDE = np.array(SIDE, np.int8)[o]
    SLP = np.array(SLP, np.float64)[o]
    TPP = np.array(TPP, np.float64)[o]
    m = len(I)
    return Signals(i=I, side=SIDE, kind=np.zeros(m, int), level=mid[I],
                   sl_pts=SLP, tp_pts=TPP, ttl=np.zeros(m, np.int64))
