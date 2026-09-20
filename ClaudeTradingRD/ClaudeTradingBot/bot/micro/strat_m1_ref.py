"""M1 REFERENCE / TEMPLATE — z-score mean reversion (maker fade).

Validates the M1 timeframe path (TF=60). A natural M1 pattern the 5s noise floor
suppressed: fade an over-extension beyond N*std from a rolling mean, in session,
with a structure stop and a mean-revert target. Copy & edit for M1/M5 candidates.

Set TF to the bar size in seconds (60=M1, 300=M5). The runner resamples the S5
bid/ask data to that timeframe and feeds it to generate() exactly like S5.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask

NAME = "m1_zscore_mr"
TF = 60   # <-- M1 execution timeframe (seconds)

SIM = dict(maxhold=60, dollars_per_point=1.0, commission=0.07, cooldown=2)

LOOKBACK = 40       # M1 bars for mean/std (~40 min)
Z_IN = 2.2          # enter when |mid-mean| >= Z_IN*std
SL_PTS = 3.5
TP_PTS = 2.5
TTL = 5
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)


def _roll_mean_std(x, w):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    mean = np.full(len(x), np.nan); std = np.full(len(x), np.nan)
    if len(x) > w:
        win = swv(x[:-1], w)               # causal: excludes current bar
        mean[w:] = win.mean(axis=1)
        std[w:] = win.std(axis=1)
    return mean, std


def generate(b: Bars) -> Signals:
    mid = b.mid
    mean, std = _roll_mean_std(mid, LOOKBACK)
    sess = hours_mask(b, SESSION_HOURS)
    z = (mid - mean) / np.where(std > 0, std, np.nan)
    ok = np.isfinite(z) & sess
    short = ok & (z >= Z_IN)     # over-extended up -> fade short (sell-limit at mid)
    long_ = ok & (z <= -Z_IN)    # over-extended down -> fade long

    iu = np.where(short)[0]; il = np.where(long_)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    # maker limit at current mid (fade the extension on a small further push)
    level = np.concatenate([mid[iu], mid[il]])
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(i=i, side=side, kind=np.ones(n, int), level=level,
                   sl_pts=np.full(n, SL_PTS), tp_pts=np.full(n, TP_PTS),
                   ttl=np.full(n, TTL, np.int64))
