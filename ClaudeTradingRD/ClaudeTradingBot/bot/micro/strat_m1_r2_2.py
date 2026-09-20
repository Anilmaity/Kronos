"""Session-VWAP fair-value pullback, trend-aligned (M1) -- BEST-HONEST config.

The cleanest deployable form of "session VWAP deviation reversion" on a trending
instrument: use the day-anchored VWAP as a fair-value magnet. In a higher-TF
UPtrend, when price trades above VWAP within a pullback band, arm a BUY LIMIT at
VWAP and ride continuation; mirror SELL LIMIT at VWAP in a downtrend. In-session
only; clear-trend only (flat/ambiguous -> stand aside). Maker limit earns spread.

HONEST VERDICT (this run): NO TAKER EDGE. A full param sweep (sweep_r2_2.py) over
trend-slope / pullback-band / stop / target / ttl could not push the ~0.25-taker
PF above ~0.81 in EITHER train or OOS -- and even the 0.20-spread MAKER PF stays
below 1.0 (~0.95 best), i.e. there is essentially no gross edge before cost. This
reproduces the m1_vwap_dev_revert dead-end and the project memory "mean-rev sits at
the cost floor". Gold trends hard 2024-26, so VWAP reversion has nothing to capture
once the spread is paid. Parameters below are the highest-honest config found; it
is reported as a NON-PASS, not a deployable edge.

Causal: vwap[i], sigma[i], ema[i]/slope use bars <= i; the limit arms at close[i]
and fills only on a later bar (i+1..i+TTL). No future indexing.
"""
import numpy as np
from bot.micro.engine import Bars, Signals
from bot.micro.features import hours_mask, ema

NAME = "m1_svwap_fairvalue_pullback"
TF = 60   # M1

SIM = dict(maxhold=60, dollars_per_point=1.0, commission=0.07, cooldown=5)

SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)  # London + NY
DEV_W = 40
EMA_LONG = 150     # ~2.5h trend proxy
TREND_W = 60       # EMA slope lookback
TREND_MIN = 0.6    # min |ema slope| (pts) to call a trend
DEV_LO = 0.8       # arm only when price is this far past VWAP (sigma units)
DEV_HI = 2.0       # ...but not already over-extended
SL_PTS = 3.0
TP_PTS = 4.5
TTL = 10           # bars the VWAP limit stays live


def _session_vwap(b: Bars):
    day = b.day
    mid = b.mid
    vol = np.where(b.vol > 0, b.vol.astype(np.float64), 1.0)
    vwap = np.empty(b.n)
    cum_pv = 0.0
    cum_v = 0.0
    cur = day[0]
    for i in range(b.n):
        if day[i] != cur:
            cur = day[i]
            cum_pv = 0.0
            cum_v = 0.0
        cum_pv += mid[i] * vol[i]
        cum_v += vol[i]
        vwap[i] = cum_pv / cum_v
    return vwap


def _roll_std(x, w):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    out = np.full(len(x), np.nan)
    if len(x) >= w:
        out[w - 1:] = swv(x, w).std(axis=1)
    return out


def generate(b: Bars) -> Signals:
    mid = b.mid
    vwap = _session_vwap(b)
    dev = mid - vwap
    sigma = _roll_std(dev, DEV_W)

    emal = ema(mid, EMA_LONG)
    slope = np.full(b.n, np.nan)
    slope[TREND_W:] = emal[TREND_W:] - emal[:-TREND_W]

    sess = hours_mask(b, SESSION_HOURS)
    good = np.isfinite(sigma) & (sigma > 0) & np.isfinite(slope) & sess
    z = dev / np.where(sigma > 0, sigma, np.nan)

    long_ = good & (slope >= TREND_MIN) & (z >= DEV_LO) & (z <= DEV_HI)
    short = good & (slope <= -TREND_MIN) & (z <= -DEV_LO) & (z >= -DEV_HI)

    il = np.where(long_)[0]
    iu = np.where(short)[0]
    i = np.concatenate([il, iu])
    side = np.concatenate([np.ones(len(il), int), -np.ones(len(iu), int)])
    level = np.concatenate([vwap[il], vwap[iu]])   # limit AT fair value
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(i=i, side=side, kind=np.ones(n, int), level=level,
                   sl_pts=np.full(n, SL_PTS), tp_pts=np.full(n, TP_PTS),
                   ttl=np.full(n, TTL, np.int64))
