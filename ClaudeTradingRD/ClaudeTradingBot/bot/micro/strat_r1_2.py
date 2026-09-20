"""Volume-spike ABSORPTION fade  (candidate r1_2).

CONCEPT (as assigned): a 5-second bar prints volume >> its rolling mean (a spike)
while testing a liquidity level, yet FAILS to extend price -- the aggressive flow
is absorbed and the bar closes back inside the level. Fade that exhaustion.

PRECISE, FULLY-SPECIFIED RULES (all causal -- only bar i's close is used):
  rolling vol mean  : vmean[i] = mean(vol[i-W_VOL : i])              (causal, excl i)
  volume spike      : vol[i] >= VSPIKE * vmean[i]
  liquidity level   : rmax/rmin = causal rolling max/min of mid over LOOKBACK bars
  up-side sweep+fail : ah[i] > rmax  (took liquidity above)  AND
                       bc[i] <= rmax - MIN_REVERT  (closed back below the level) AND
                       close in lower part of bar: (bc-bl)/(bh-bl) <= CLPOS
  down-side mirror   : al[i] < rmin AND bc[i] >= rmin + MIN_REVERT AND
                       (bh-bc)/(bh-bl) <= CLPOS
  HTF-bias gate     : only fade INTO the higher-timeframe trend (EMA on mid):
                       short up-sweeps only when mid < ema (downtrend);
                       long  down-sweeps only when mid > ema (uptrend).
                       This makes the fade a stop-raid reversal that runs WITH the
                       larger trend, not a counter-trend knife-catch.
  entry             : MAKER limit (kind=1) -- sell into a small bounce LEVOFF above
                       the absorption-bar close (buy into a dip below it). Earns the
                       spread and gets a better fill than chasing.
  exit              : fixed SL_PTS / TP_PTS; engine pays real bid/ask both sides.

HONEST NOTE: extensive pre-testing (see report) shows this fade has NO taker edge on
XAU S5 -- the high-volume level test is overwhelmingly a genuine break that
CONTINUES (~30% WR for the fade). The maker-into-trend variant below is the least-bad,
most-faithful implementation; the runner documents whether any edge survives OOS.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view as swv
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import hours_mask, ema

NAME = "vol_absorption_fade"

SIM = dict(maxhold=180, dollars_per_point=1.0, commission=0.07, cooldown=6)

# --- tunable params (runner sweeps these +/-30%) ---
W_VOL = 60          # rolling-vol-mean window (5 min of 5s bars)
VSPIKE = 2.5        # spike threshold: vol >= VSPIKE * rolling mean
LOOKBACK = 50       # bars defining the liquidity level
MIN_REVERT = 0.10   # close must be back inside the swept level by this many pts
CLPOS = 0.6         # close must sit in the rejected end of the bar (<= this fraction)
EMA_TREND = 600     # HTF-bias EMA on mid (~50 min)
LEVOFF = 0.30       # maker limit offset from the absorption close (pts)
SL_PTS = 2.0
TP_PTS = 3.0
TTL = 24            # bars the limit stays live
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active hours (UTC)


def generate(b: Bars) -> Signals:
    n = b.n
    vmean = np.full(n, np.nan)
    if n > W_VOL:
        vmean[W_VOL:] = swv(b.vol[:-1].astype(np.float64), W_VOL).mean(axis=1)
    finv = np.isfinite(vmean)
    spike = (b.vol >= VSPIKE * vmean) & finv

    rmax = roll_max(b.mid, LOOKBACK)
    rmin = roll_min(b.mid, LOOKBACK)
    es = ema(b.mid, EMA_TREND)
    sess = hours_mask(b, SESSION_HOURS)
    rng = np.maximum(b.bh - b.bl, 1e-6)
    clpos_up = (b.bc - b.bl) / rng     # near 0 -> closed at the low (rejected the high)
    clpos_dn = (b.bh - b.bc) / rng     # near 0 -> closed at the high (rejected the low)

    # up-side absorption -> fade SHORT, only in a downtrend (fade into HTF bias)
    up = (b.ah > rmax) & (b.bc <= rmax - MIN_REVERT) & np.isfinite(rmax) \
        & spike & sess & (clpos_up <= CLPOS) & (b.mid < es)
    # down-side absorption -> fade LONG, only in an uptrend
    dn = (b.al < rmin) & (b.bc >= rmin + MIN_REVERT) & np.isfinite(rmin) \
        & spike & sess & (clpos_dn <= CLPOS) & (b.mid > es)

    iu = np.where(up)[0]
    il = np.where(dn)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    # maker level: sell into a bounce above the close / buy into a dip below it
    level = np.concatenate([b.bc[iu] + LEVOFF, b.bc[il] - LEVOFF])
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    m = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(m, int),               # maker limit entry
        level=level,
        sl_pts=np.full(m, SL_PTS),
        tp_pts=np.full(m, TP_PTS),
        ttl=np.full(m, TTL),
    )
