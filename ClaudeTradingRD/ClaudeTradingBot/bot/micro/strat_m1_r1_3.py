"""Session-anchored VWAP deviation reversion (M1 maker fade).

CONCEPT
-------
Build a session-anchored VWAP from M1 (sum(price*vol)/sum(vol), reset at the
start of the London+NY session each UTC day). When mid extends beyond k*ATR from
the running VWAP, fade it with a deep maker limit, targeting reversion toward the
VWAP. Only in-session, and only when the higher-TF context is BALANCED (the slow
EMA is flat / price is not trending hard away from VWAP) -- mean reversion only
pays inside a range, not into a trend.

NO LOOK-AHEAD: VWAP[i] uses cumulative price*vol THROUGH bar i (causal); ATR is
Wilder-causal; the balance gate reads a past-only EMA and a causal VWAP slope;
every entry is a limit acted on the bar AFTER its decision bar and filled by the
engine next-bar. Absolute imports. generate(b)->Signals, SIM, NAME, TF.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import hours_mask, ema

NAME = "m1_vwap_dev_revert"
TF = 60   # M1 execution timeframe (seconds)


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


SIM = dict(maxhold=_P("VW_MAXHOLD", 45, int), dollars_per_point=1.0,
           commission=0.07, cooldown=_P("VW_COOLDOWN", 2, int))

SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("VW_HOURS", "7,8,9,10,11,12,13,14,15").split(","))
# NOTE: defaults below are the STRONGEST-honest config found by bot/micro/sweep_vwap.py
# (max of min(train,oos) taker PF@~0.25 over a 324-cell grid). It still FAILS the bar
# (train PF 0.725 / oos PF 0.953, both < 1) -- fading VWAP extensions has no taker edge.
ATR_P    = _P("VW_ATRP", 14, int)
K_BAND   = _P("VW_K", 2.5)          # enter when |mid-vwap| >= K_BAND * ATR
TP_FRAC  = _P("VW_TPFRAC", 0.8)     # target = TP_FRAC of the way back to VWAP
SL_ATR   = _P("VW_SLATR", 2.0)      # stop distance = SL_ATR * ATR
OFF_ATR  = _P("VW_OFF", 0.8)        # rest fade limit OFF_ATR*ATR further out (catch the sweep)
TTL      = _P("VW_TTL", 6, int)
WARMUP   = _P("VW_WARMUP", 10, int) # min in-session bars before VWAP is trusted
# balance gate: session is "balanced" when slow EMA is close to VWAP (not trending)
BIAS_EMA = _P("VW_BIAS", 240, int)  # slow EMA (~4h on M1)
BAL_ATR  = _P("VW_BAL", 2.5)        # |ema-vwap| must be < BAL_ATR*ATR to fade
SLOPE_LB = _P("VW_SLOPELB", 20, int)   # VWAP-slope window (bars)
SLOPE_MAX = _P("VW_SLOPEMAX", 1.2)     # |vwap[i]-vwap[i-lb]| must be < SLOPE_MAX*ATR
EXT_LB   = _P("VW_EXTLB", 0, int)      # fresh-extreme lookback (0=off)


def _ffill(a):
    idx = np.where(~np.isnan(a), np.arange(len(a)), 0)
    np.maximum.accumulate(idx, out=idx)
    return a[idx]


def _session_vwap(b: Bars, sess):
    """Cumulative VWAP anchored at each day's session start. Causal."""
    v = b.vol.astype(np.float64)
    pv = b.mid * v
    cpv = np.cumsum(pv); cv = np.cumsum(v)
    prefix_pv = np.concatenate(([0.0], cpv))
    prefix_v = np.concatenate(([0.0], cv))
    # rising edge of session = anchor (bar0 counts if in-session)
    start = sess & np.concatenate(([True], ~sess[:-1]))
    base_pv = np.full(b.n, np.nan); base_v = np.full(b.n, np.nan)
    si = np.where(start)[0]
    base_pv[si] = prefix_pv[si]; base_v[si] = prefix_v[si]
    base_pv = _ffill(base_pv); base_v = _ffill(base_v)
    cum_pv = cpv - base_pv; cum_v = cv - base_v
    # bars-since-anchor (for warmup)
    pos = np.arange(b.n)
    base_idx = np.full(b.n, np.nan); base_idx[si] = si.astype(float)
    base_idx = _ffill(base_idx)
    nsince = pos - base_idx
    vwap = np.where(cum_v > 0, cum_pv / np.where(cum_v > 0, cum_v, 1.0), np.nan)
    return vwap, nsince


def _causal_prev(x, lb):
    """x[i-lb] (NaN for i<lb), causal."""
    out = np.full(len(x), np.nan)
    if lb < len(x):
        out[lb:] = x[:-lb]
    return out


def generate(b: Bars) -> Signals:
    mid = b.mid
    a = atr(b, ATR_P)
    sess = hours_mask(b, SESSION_HOURS)
    vwap, nsince = _session_vwap(b, sess)
    Eb = ema(mid, BIAS_EMA)

    dev = mid - vwap
    band = K_BAND * a
    balanced = np.abs(Eb - vwap) < (BAL_ATR * a)
    # VWAP-slope gate: session must be rotational (flat VWAP), not trending
    vwap_prev = _causal_prev(vwap, SLOPE_LB)
    flat = np.abs(vwap - vwap_prev) < (SLOPE_MAX * a)
    ok = (np.isfinite(vwap) & np.isfinite(a) & (a > 0) & sess
          & (nsince >= WARMUP) & balanced & flat & np.isfinite(vwap_prev))

    # fresh-extreme gate: only fade a push that makes a new EXT_LB-bar extreme (a sweep)
    if EXT_LB > 0:
        from bot.micro.engine import roll_max, roll_min
        rmx = roll_max(mid, EXT_LB); rmn = roll_min(mid, EXT_LB)
        new_hi = np.isfinite(rmx) & (mid >= rmx)
        new_lo = np.isfinite(rmn) & (mid <= rmn)
    else:
        new_hi = np.ones(b.n, bool); new_lo = np.ones(b.n, bool)

    short = ok & (dev >= band) & new_hi    # extended up + fresh high -> fade short
    long_ = ok & (dev <= -band) & new_lo   # extended down + fresh low -> fade long

    iu = np.where(short)[0]; il = np.where(long_)[0]
    i = np.concatenate([iu, il])
    if len(i) == 0:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    devmag = np.abs(dev[i])
    # rest the fade limit OFF_ATR*ATR further out: sell-limit ABOVE (short),
    # buy-limit BELOW (long) -> only fills on a further push (the sweep), better price.
    level = mid[i] - side * (OFF_ATR * a[i])
    # target: revert toward VWAP from the FILL level (dev grows by the offset)
    tp = np.maximum(0.4, (devmag + OFF_ATR * a[i]) * TP_FRAC)
    sl = np.maximum(0.5, a[i] * SL_ATR)

    o = np.argsort(i, kind="stable")
    i, side, level, tp, sl = i[o], side[o], level[o], tp[o], sl[o]
    n = len(i)
    return Signals(i=i, side=side, kind=np.ones(n, int), level=level,
                   sl_pts=sl, tp_pts=tp, ttl=np.full(n, TTL, np.int64))
