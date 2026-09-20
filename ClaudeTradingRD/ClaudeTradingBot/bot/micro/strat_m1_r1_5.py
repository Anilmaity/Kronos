"""Confirmed spike-reversion (r1_5).

All four limit-fade variants failed by ADVERSE SELECTION: a resting fade limit fills
precisely on the breakouts that keep going, so WR collapses. Flip the mechanic to a
CONFIRMATION entry that can only trigger once reversion is already underway:

  - Spike+sweep: the prior bar pushed past Z_IN std AND swept a recent rolling
    extreme (stop-run liquidity grab).
  - Reclaim: the CURRENT bar closes back across the prior bar's opposite extreme
    (close > prior-high for longs) -> the snap-back has started; we join it, we are
    never filled on continuation.
  - Bias: only WITH the higher-TF mean (longs when mid < slow EMA, revert up).
  - Session: London/NY.
  - Stop beyond the spike extreme (structure); target reverts toward the local mean.

Maker limit at the close mid; runner grid re-prices taker. TF=60.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import hours_mask, ema

NAME = "m1_confirmed_spike_rev"
TF = 60

SIM = dict(maxhold=40, dollars_per_point=1.0, commission=0.07, cooldown=3)

LOOKBACK = 40
Z_IN = 2.0
EMA_SLOW = 120
SWEEP_W = 20
SL_BUF = 1.0
SL_MAX = 4.0         # cap structure stop
TP_MIN = 1.5
TP_MAX = 8.0
RR_MIN = 1.0         # require target >= stop (skip low-R)
ER_W = 30
ER_MAX = 0.40        # range regime only
SIDE = 0             # 0=both, +1 long-only, -1 short-only
TTL = 3
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)


def _eff_ratio(x, w):
    n = len(x); er = np.full(n, np.nan)
    d = np.abs(np.diff(x))
    from numpy.lib.stride_tricks import sliding_window_view as swv
    if n > w + 1:
        vol = swv(d, w).sum(axis=1)
        net = np.abs(x[w:] - x[:-w])
        er[w:] = net / np.where(vol > 0, vol, np.nan)
    return er


def _roll_mean_std(x, w):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    mean = np.full(len(x), np.nan); std = np.full(len(x), np.nan)
    if len(x) > w:
        win = swv(x[:-1], w)
        mean[w:] = win.mean(axis=1); std[w:] = win.std(axis=1)
    return mean, std


def generate(b: Bars) -> Signals:
    mid = b.mid
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    mean, std = _roll_mean_std(mid, LOOKBACK)
    z = (mid - mean) / np.where(std > 0, std, np.nan)
    es = ema(mid, EMA_SLOW)
    rmin = roll_min(b.bl, SWEEP_W)
    rmax = roll_max(b.ah, SWEEP_W)
    er = _eff_ratio(mid, ER_W)
    sess = hours_mask(b, SESSION_HOURS)
    okbase = sess & np.isfinite(mean) & np.isfinite(es) & np.isfinite(z) \
        & np.isfinite(er) & (er <= ER_MAX)

    n = b.n
    # prior-bar spike & sweep, current-bar reclaim of prior extreme
    prev = np.zeros(n, bool); prev[1:] = True
    spike_dn = np.zeros(n, bool); spike_up = np.zeros(n, bool)
    spike_dn[1:] = (z[:-1] <= -Z_IN) & (b.bl[:-1] <= rmin[:-1])
    spike_up[1:] = (z[:-1] >= Z_IN) & (b.ah[:-1] >= rmax[:-1])
    reclaim_up = np.zeros(n, bool); reclaim_dn = np.zeros(n, bool)
    reclaim_up[1:] = b.bc[1:] > b.ah[:-1]      # close above prior high
    reclaim_dn[1:] = b.ac[1:] < b.bl[:-1]      # close below prior low

    long_ = okbase & spike_dn & reclaim_up & (mid < es)
    short = okbase & spike_up & reclaim_dn & (mid > es)
    if SIDE > 0:
        short[:] = False
    elif SIDE < 0:
        long_[:] = False

    il = np.where(long_)[0]; iu = np.where(short)[0]
    # structure stop below the prior spike low / above prior spike high (capped)
    sl_l = np.clip((mid[il] - lo[il - 1]) + SL_BUF, TP_MIN, SL_MAX)
    sl_u = np.clip((hi[iu - 1] - mid[iu]) + SL_BUF, TP_MIN, SL_MAX)
    tp_l = np.clip(mean[il] - mid[il], TP_MIN, TP_MAX)
    tp_u = np.clip(mid[iu] - mean[iu], TP_MIN, TP_MAX)

    i = np.concatenate([il, iu])
    side = np.concatenate([np.ones(len(il), int), -np.ones(len(iu), int)])
    level = np.concatenate([mid[il], mid[iu]])
    sl_pts = np.concatenate([sl_l, sl_u])
    tp_pts = np.concatenate([tp_l, tp_u])
    # require reward:risk >= RR_MIN
    keep = tp_pts >= RR_MIN * sl_pts
    i, side, level, sl_pts, tp_pts = i[keep], side[keep], level[keep], sl_pts[keep], tp_pts[keep]

    o = np.argsort(i, kind="stable")
    i, side, level, sl_pts, tp_pts = i[o], side[o], level[o], sl_pts[o], tp_pts[o]
    m = len(i)
    return Signals(i=i, side=side, kind=np.ones(m, int), level=level,
                   sl_pts=sl_pts, tp_pts=tp_pts, ttl=np.full(m, TTL, np.int64))
