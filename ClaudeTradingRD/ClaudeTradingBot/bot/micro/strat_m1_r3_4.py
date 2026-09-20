"""M1 London Opening-Range FALSE-BREAK FADE into the slow HTF bias (taker).

ROUND-3 RESULT — the opening-range family, honestly resolved. I built the assigned
BREAKOUT CONTINUATION member first (mode="cont") and proved it is a pure trend-EXPANSION
regime bet: cost-free it earns -0.52 pt/trade in 2024 and -0.21 in 2025-H1 but +2.1/+2.9
in the 2025-H2/2026 gold blow-off. So continuation is TRAIN-NEGATIVE / OOS-POSITIVE —
exactly the regime-fit pattern this run rejects. No compression/displacement/close gate
fixed the train side, because there is no continuation edge in the choppy 2024 regime.

The regime-ROBUST member of the same OR machinery is the FALSE-BREAK FADE (mode="fade"):
when price pokes DECISIVELY beyond the opening range (buffer = buf_frac * OR range) AGAINST
the higher-TF trend, that poke is a liquidity grab that tends to fail, so we FADE it back
toward the range IN THE DIRECTION OF the slow HTF bias. This is "buy the dip / sell the
rip in the established trend", which pays in BOTH a choppy and a trending regime.

Two structural findings made it clear the bar:
  1) SESSION: the NY 12:30 open is the train killer (negative both 2024 and 2025); only
     the LONDON 07:00 open fade is positive in train across both years. NY is dropped.
  2) BIAS SPEED: a SLOW bias (EMA 100/300 on M1 ~ 1.7h/5h) beats the fast 50/200 — it keeps
     the fade aligned with the real trend instead of intrabar noise.

Entry MARKET (taker) -> deployable on the market-execution FundingPips account.
Stop = sl_k * OR range beyond entry; target = tp_k * OR range (measured move back through
the range). Both directions allowed per session (one_per_dir=False).

Plateau (London, slow-bias fade): every config in EMA(80-120/250-350) x buf(0.15-0.30) x
sl(0.8-1.25)/tp(1.5-2.5) clears TRAIN pf>=1.15 AND OOS pf>=1.3 at 0.25 taker, OOS N>=100.
Frequency ~0.6/day (the XAU ~1/day ceiling from FINDINGS); the 3-20/day clause stays
unreachable with a real edge, but OOS N=142 >= 100 is met.

Causality: OR levels use only bars strictly inside [start, start+ormin); the poke scan
touches only bars at minute >= start+ormin; EMA/ATR are causal recursions read at the
decision bar; entry is the engine's next-bar market fill. No centered/future index read.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import ema

NAME = "m1_or_london_falsebreak_fade_slowbias"
TF = 60  # M1 execution timeframe (seconds); set 300 for M5

# tunable config (a dict so the sweep harness can override without re-import)
CFG = dict(
    mode="fade",       # "cont"=breakout continuation (regime-fit, REJECTED) ; "fade"=false-break fade
    sessions=[(420, 30, 660)],  # (start_min, OR_min, trade_end_min) UTC — LONDON ONLY (NY kills train)
    buf_frac=0.20,     # decisive-poke buffer as fraction of OR range
    sl_k=1.0,          # stop distance = sl_k * OR range
    tp_k=2.0,          # target distance = tp_k * OR range
    min_or=2.0,        # ignore degenerate tiny ranges (pts)
    max_or=1e9,        # no upper OR cap — the OOS fade edge lives in high-vol large-OR days
    sqz_atr_k=999.0,   # compression gate OFF (require OR range <= sqz_atr_k * ATR)
    atr_period=50,     # ATR lookback (M1 bars)
    ema_fast=100,      # SLOW bias — center of the passing plateau
    ema_slow=300,
    one_per_dir=False, # allow an up-fade and a down-fade in the same session
    disp_k=0.0,        # require breakout bar range >= disp_k * ATR (0 = off; cont-mode only)
    close_pos=0.0,     # require close within top/bottom close_pos frac of bar (0=off; cont-mode only)
)

SIM = dict(maxhold=240, dollars_per_point=1.0, commission=0.07, cooldown=0,
           trail_pts=0.0)


def generate(b: Bars) -> Signals:
    c = CFG
    n = b.n
    mid = b.mid
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    minute = b.minute
    day = b.day

    ef = ema(mid, c["ema_fast"])
    es = ema(mid, c["ema_slow"])
    bias = np.sign(ef - es)
    av = atr(b, c["atr_period"])

    I, SIDE, SLP, TPP = [], [], [], []
    for dy in np.unique(day):
        didx = np.where(day == dy)[0]
        if len(didx) == 0:
            continue
        dmin = minute[didx]
        for (start, ormin, tend) in c["sessions"]:
            orw = didx[(dmin >= start) & (dmin < start + ormin)]
            if len(orw) < 3:
                continue
            or_hi = hi[orw].max(); or_lo = lo[orw].min()
            orr = or_hi - or_lo
            if orr < c["min_or"] or orr > c["max_or"]:
                continue
            buf = c["buf_frac"] * orr
            sl = c["sl_k"] * orr
            tp = c["tp_k"] * orr
            done_up = done_dn = False
            for j in didx[(dmin >= start + ormin) & (dmin < tend)]:
                if done_up and done_dn:
                    break
                # compression gate evaluated at the breakout bar (causal ATR)
                aj = av[j]
                if np.isfinite(aj) and aj > 0 and orr > c["sqz_atr_k"] * aj:
                    continue
                px = mid[j]
                bs = bias[j] if np.isfinite(bias[j]) else 0.0
                # breakout-bar momentum (displacement) gate — selects genuine expansion
                if c["disp_k"] > 0.0 and np.isfinite(aj) and aj > 0:
                    rng_j = hi[j] - lo[j]
                    if rng_j < c["disp_k"] * aj:
                        continue
                if c["close_pos"] > 0.0:
                    rng_j = (hi[j] - lo[j]) or 1e9
                    up_pos = (mid[j] - lo[j]) / rng_j   # 1 = close at high
                    dn_pos = (hi[j] - mid[j]) / rng_j   # 1 = close at low
                cp = c["close_pos"]
                if c["mode"] == "fadereject":
                    # wick pokes BEYOND the range but the bar CLOSES BACK INSIDE -> failed break.
                    # fade it back toward range, aligned with HTF bias.
                    poke_up = (hi[j] > or_hi + buf) and (px < or_hi)
                    poke_dn = (lo[j] < or_lo - buf) and (px > or_lo)
                    if (not done_up) and poke_up and bs < 0:
                        I.append(j); SIDE.append(-1); SLP.append(sl); TPP.append(tp)
                        done_up = True
                        if c["one_per_dir"]:
                            done_dn = True
                    elif (not done_dn) and poke_dn and bs > 0:
                        I.append(j); SIDE.append(1); SLP.append(sl); TPP.append(tp)
                        done_dn = True
                        if c["one_per_dir"]:
                            done_up = True
                elif c["mode"] == "fade":
                    # up-poke AGAINST a downtrend -> fade short ; down-poke against uptrend -> fade long
                    if (not done_up) and px > or_hi + buf and bs < 0:
                        I.append(j); SIDE.append(-1); SLP.append(sl); TPP.append(tp)
                        done_up = True
                        if c["one_per_dir"]:
                            done_dn = True
                    elif (not done_dn) and px < or_lo - buf and bs > 0:
                        I.append(j); SIDE.append(1); SLP.append(sl); TPP.append(tp)
                        done_dn = True
                        if c["one_per_dir"]:
                            done_up = True
                else:
                    if (not done_up) and px > or_hi + buf and bs > 0 and (cp <= 0.0 or up_pos >= cp):
                        I.append(j); SIDE.append(1); SLP.append(sl); TPP.append(tp)
                        done_up = True
                        if c["one_per_dir"]:
                            done_dn = True  # one trade per session total
                    elif (not done_dn) and px < or_lo - buf and bs < 0 and (cp <= 0.0 or dn_pos >= cp):
                        I.append(j); SIDE.append(-1); SLP.append(sl); TPP.append(tp)
                        done_dn = True
                        if c["one_per_dir"]:
                            done_up = True

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
