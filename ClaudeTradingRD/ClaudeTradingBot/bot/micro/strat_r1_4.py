"""Equal-highs / equal-lows RAID-AND-REVERSE on XAU S5.

CONCEPT (assigned): a cluster of (near-)equal swing highs or equal swing lows
forms a resting-liquidity pool (buy-stops above equal highs, sell-stops below
equal lows). Price RAIDS the pool (wicks through it) and REJECTS (closes back
inside). We fade the raid: short the equal-highs sweep, long the equal-lows sweep.

WHY THIS COULD HAVE AN EDGE (vs the dead naive sweep, per SCOUT_FINDINGS):
  - The level is a *confirmed-swing* cluster that HELD twice (genuine resting
    liquidity), not a rolling-N extreme that just tracks the trend.
  - We require a real rejection (close back inside by MIN_REVERT) -> filters out
    pure continuation breakouts.
  - HTF EMA bias gate -> only fade highs when bias is not strongly up, only buy
    lows when bias is not strongly down (asymmetry, avoids knife-catching).

CAUSALITY:
  - Structure is built on resampled M5 mid bars. Swings are CENTERED (k bars) so a
    swing at M5 index j is only referenced from its confirmation bar j+k, whose
    last S5 index is the pool's start; pools are active only from that S5 bar on.
  - Pool levels for bar i come from np.searchsorted (most recent event with
    start<=i, within TTL). No future info touches bar i.

Entry is MARKET on the rejection bar (taker, deployable on FundingPips MT5).
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import resample, swings, hours_mask, ema

NAME = "eqhl_raid"

SIM = dict(maxhold=180, dollars_per_point=1.0, commission=0.07, cooldown=60,
           trail_pts=0.0, be_at_pts=0.0)

# ---- tunable params (runner / sweeps vary these +-30%) ----
M5_SEC = 300          # structure timeframe (seconds)
SW_K = 2              # fractal half-width on M5 (confirm lag)
EQ_TOL = 0.15         # equal-highs/lows tolerance as fraction of M5 ATR
POOL_TTL = 2400       # S5 bars a pool stays live (~200 min)
MIN_REVERT = 0.6      # pts price must close back inside the swept level
SL_PTS = 2.0
TP_PTS = 3.0
ATR_LO, ATR_HI = 0.12, 1.6   # S5 ATR(14) band (pts)
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active (UTC)
BIAS_EMA = 1800       # S5 EMA period for HTF bias gate (0 = disabled)
VOL_MULT = 1.5        # absorption: sweep-bar vol >= VOL_MULT * rolling-median vol
VOL_WIN = 360         # rolling-median window for the absorption test (bars)


def _m5_atr(o, h, l, c, period=14):
    n = len(c)
    pc = np.empty(n); pc[0] = c[0]; pc[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    out = np.empty(n); a = 1.0 / period; out[0] = tr[0]
    for i in range(1, n):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
    return out


def _pool_events(idx, price, conf, mat, tol_frac, is_high):
    """Build (start_s5, level) events where swing #j is (near-)equal to swing
    #j-1 or #j-2. level = the liquidity edge (max for highs, min for lows)."""
    starts = []
    levels = []
    for back in (1, 2):
        if len(idx) <= back:
            continue
        dp = np.abs(price[back:] - price[:-back])
        tol = tol_frac * mat[back:]
        eq = np.where(dp <= tol)[0] + back   # index of the later swing
        if is_high:
            lv = np.maximum(price[eq], price[eq - back])
        else:
            lv = np.minimum(price[eq], price[eq - back])
        starts.append(conf[eq]); levels.append(lv)
    if not starts:
        return np.array([], np.int64), np.array([], np.float64)
    s = np.concatenate(starts); l = np.concatenate(levels)
    o = np.argsort(s, kind="stable")
    return s[o], l[o]


def _active_level(n, starts, levels, ttl):
    """For each S5 bar, level of the most recent pool event with start<=i and
    age<=ttl. Fully causal & vectorized."""
    out = np.full(n, np.nan)
    if len(starts) == 0:
        return out
    ar = np.arange(n)
    j = np.searchsorted(starts, ar, side="right") - 1
    valid = j >= 0
    jc = j.clip(0)
    lev = levels[jc]
    st = starts[jc]
    age = ar - st
    ok = valid & (age <= ttl)
    out[ok] = lev[ok]
    return out


def generate(b: Bars) -> Signals:
    A5 = atr(b, 14)
    M = resample(b, M5_SEC)
    mo, mh, ml, mc = M["o"], M["h"], M["l"], M["c"]
    s5idx = M["s5_idx"]
    K = len(mc)
    mat = _m5_atr(mo, mh, ml, mc, 14)

    sh, sl = swings(mh, ml, SW_K)

    # swing-high list with confirmation S5 index
    shi = np.where(sh)[0]; shi = shi[shi + SW_K < K]
    sli = np.where(sl)[0]; sli = sli[sli + SW_K < K]
    eqh_s, eqh_l = _pool_events(shi, mh[shi], s5idx[shi + SW_K], mat[shi],
                                EQ_TOL, True)
    eql_s, eql_l = _pool_events(sli, ml[sli], s5idx[sli + SW_K], mat[sli],
                                EQ_TOL, False)

    eqh_level = _active_level(b.n, eqh_s, eqh_l, POOL_TTL)   # short pool (highs)
    eql_level = _active_level(b.n, eql_s, eql_l, POOL_TTL)   # long pool (lows)

    mhigh = (b.ah + b.bh) * 0.5
    mlow = (b.al + b.bl) * 0.5
    mclose = b.mid

    sess = hours_mask(b, SESSION_HOURS)
    volok = (A5 >= ATR_LO) & (A5 <= ATR_HI)

    if BIAS_EMA > 0:
        be = ema(b.mid, BIAS_EMA)
        bias_dn = mclose < be       # allow shorts (fade highs) when below bias
        bias_up = mclose > be       # allow longs (buy lows) when above bias
    else:
        bias_dn = np.ones(b.n, bool); bias_up = np.ones(b.n, bool)

    sweep_up = (np.isfinite(eqh_level) & (mhigh > eqh_level) &
                (mclose < eqh_level - MIN_REVERT) & sess & volok & bias_dn)
    sweep_dn = (np.isfinite(eql_level) & (mlow < eql_level) &
                (mclose > eql_level + MIN_REVERT) & sess & volok & bias_up)

    if VOL_MULT > 0:
        v = b.vol.astype(np.float64)
        rv = np.full(b.n, np.nan)
        if b.n > VOL_WIN:
            from numpy.lib.stride_tricks import sliding_window_view as swv
            rv[VOL_WIN:] = np.median(swv(v[:-1], VOL_WIN), axis=1)
        absorb = v >= VOL_MULT * rv          # NaN compares False -> early bars excluded
        sweep_up &= absorb
        sweep_dn &= absorb

    iu = np.where(sweep_up)[0]
    il = np.where(sweep_dn)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    o = np.argsort(i, kind="stable")
    i, side = i[o], side[o]
    nsig = len(i)
    return Signals(
        i=i, side=side,
        kind=np.zeros(nsig, int),
        level=np.zeros(nsig),
        sl_pts=np.full(nsig, SL_PTS),
        tp_pts=np.full(nsig, TP_PTS),
    )
