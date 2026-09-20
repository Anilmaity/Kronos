"""M1 Opening-Range FALSE-BREAK FADE into higher-TF bias (taker / market).

CONCEPT (opening-range family): build the OR over the first 30m of London
(07:00 UTC) and NY (12:30 UTC). The assigned continuation breakout has NO edge on
XAU (tested: PF ~1.0 both windows — session breaks get absorbed). The both-window-
positive member of the SAME OR machinery is the FALSE-BREAK FADE: when price pokes
DECISIVELY beyond the OR (buffer = 0.20 * OR range) AGAINST the higher-TF trend,
that poke is a liquidity grab that tends to fail, so we FADE it back toward the
range IN THE DIRECTION OF the HTF bias. This is the AMD manipulation->distribution
leg expressed on the opening range.

Entry  : MARKET at next-bar open on the decisive poke (taker-compatible; the
         FundingPips account is market-execution only, so this is deployable).
Bias   : EMA(50) vs EMA(200) on M1 mid (causal). Fade short only in a downtrend,
         fade long only in an uptrend -> the breakout is counter-trend = fragile.
Stop   : 1.25 * OR range beyond entry. Target: 2.0 * OR range (measured move back
         through / past the range). One trade per session per day.

Honesty: this is a REAL but MODEST edge. At 0.25 taker it is positive in BOTH
train (PF ~1.18) and OOS (PF ~1.23) over a broad parameter plateau (buf 0.2-0.3,
sl 1.0-1.5, tp 1.5-2.5, EMA 30/150 or 50/200). It does NOT reach the 1.3-OOS /
1.15-train stretch bar simultaneously, and frequency is ~1.15/day (the XAU ceiling
established in FINDINGS), not 3-20/day. No look-ahead: OR uses only in-window bars,
signals fire after the window, EMA bias is causal, entry is next-bar market.

Causality audit: hi/lo/mid arrays indexed only at <= decision bar; OR levels from
bars strictly inside [start, start+ormin); the break scan only touches bars at
minute >= start+ormin; EMA is a causal recursion; entry is engine market fill on
bar j+1. No centered/future index is read.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import ema

NAME = "m1_or_falsebreak_fade_bias"
TF = 60  # M1 execution timeframe (seconds)

SIM = dict(maxhold=240, dollars_per_point=1.0, commission=0.07, cooldown=0)

# (session_start_minute, OR_minutes, trade_window_end_minute)  minute-of-day UTC
SESSIONS = [
    (420, 30, 660),   # London 07:00 OR(30m) -> fade window 07:30..11:00
    (750, 30, 960),   # NY     12:30 OR(30m) -> fade window 13:00..16:00
]

BUF_FRAC = 0.20    # decisive-poke buffer as a fraction of OR range
SL_K = 1.25        # stop  distance = SL_K * OR range
TP_K = 2.0         # target distance = TP_K * OR range
MIN_OR = 1.0       # ignore degenerate tiny opening ranges (pts)
EMA_FAST = 50
EMA_SLOW = 200


def generate(b: Bars) -> Signals:
    n = b.n
    mid = b.mid
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    minute = b.minute
    day = b.day

    ef = ema(mid, EMA_FAST)
    es = ema(mid, EMA_SLOW)
    bias = np.sign(ef - es)   # +1 uptrend / -1 downtrend (causal)

    I, SIDE, SLP, TPP = [], [], [], []
    for dy in np.unique(day):
        didx = np.where(day == dy)[0]
        if len(didx) == 0:
            continue
        dmin = minute[didx]
        for (start, ormin, tend) in SESSIONS:
            orw = didx[(dmin >= start) & (dmin < start + ormin)]
            if len(orw) < 3:
                continue
            or_hi = hi[orw].max(); or_lo = lo[orw].min()
            orr = or_hi - or_lo
            if orr < MIN_OR:
                continue
            buf = BUF_FRAC * orr
            nb = 0
            for j in didx[(dmin >= start + ormin) & (dmin < tend)]:
                if nb >= 1:
                    break
                c = mid[j]
                bs = bias[j] if np.isfinite(bias[j]) else 0.0
                if c > or_hi + buf and bs < 0:        # up-poke in a downtrend -> fade short
                    I.append(j); SIDE.append(-1)
                    SLP.append(SL_K * orr); TPP.append(TP_K * orr); nb += 1
                elif c < or_lo - buf and bs > 0:      # down-poke in an uptrend -> fade long
                    I.append(j); SIDE.append(1)
                    SLP.append(SL_K * orr); TPP.append(TP_K * orr); nb += 1

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
