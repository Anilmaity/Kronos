"""Volume-spike ABSORPTION fade at a liquidity level -> MAKER, HTF-bias gated (r2_1).

CONCEPT (assigned): a 5s bar prints volume >> its rolling mean (a spike) while
testing a liquidity extreme, yet FAILS to extend -- the aggressive flow is absorbed
and price closes back inside the level. Fade that exhaustion.

WHAT THE DATA ACTUALLY SAYS (measured 2024-01..2025-07 train, confirmed OOS) -- this
is the honest core of the candidate, not boilerplate:

  1. FORWARD EXCURSION IS ~SYMMETRIC. For high-volume bars (vol>=2-3x rolling mean)
     touching a 150-bar rolling extreme, the median 10-min forward MFE vs MAE differ
     by only ~0.07-0.10pt -- far below the ~0.66pt median S5 spread. There is no
     clean directional edge to harvest in either direction.

  2. THE FILL SELF-SELECTS AGAINST THE FADE. A taker fade loses (PF~0.5). A MAKER
     limit resting at the level is worse on win-rate: the sell-limit at resistance
     fills *precisely* when price keeps breaking UP through it (a continuation), so
     filled trades are biased to the adverse cases -- OOS WR collapses to ~25-34%.

  3. THESE ARE CONTINUATIONS, NOT REVERSALS. Trading the BREAK (market entry with
     the spike through the level) yields a higher PF (~0.56-0.64) than fading, which
     matches the scout note that a high-volume level-test is usually a genuine break.
     But it still loses net: every taker fill pays the spread, and the directional
     edge is too small to clear it. PF 0.64 OOS still = thousands in losses.

CONCLUSION: the volume-spike-absorption "fade the exhaustion" concept has NO live
edge on XAU 5s in ANY execution mode (maker fade, taker fade, taker continuation) or
direction. It joins the prior dead ends. The implementation below is the LEAST-bad,
most-faithful version -- a maker fade (earns part of the spread, and unfilled limits
cost nothing) gated to fade only INTO the higher-timeframe trend (a stop-raid that
then runs with the larger trend, not a counter-trend knife-catch). It is reported as
a documented FAILURE against the acceptance bar, with the evidence above.

PRECISE, FULLY-SPECIFIED RULES (all causal -- decision uses info up to close[i] only):
  rolling vol mean : vmean[i] = mean(vol[i-W_VOL : i])              (causal, excl i)
  volume spike     : vol[i] >= VSPIKE * vmean[i]
  liquidity level  : rmax/rmin = causal rolling max/min of mid over LOOKBACK bars
  HTF bias EMA     : es = EMA(mid, EMA_TREND)  (~50 min)
  resistance test  : bh[i] >= rmax  AND mid[i] < es  (downtrend) -> fade SHORT
  support test     : bl[i] <= rmin  AND mid[i] > es  (uptrend)   -> fade LONG
  session gate     : London + NY active hours (UTC)
  ENTRY  : MAKER limit (kind=1). Short rests at rmax + LEVOFF; long at rmin - LEVOFF.
  EXIT   : fixed SL_PTS / TP_PTS; engine pays real bid/ask on both sides.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view as swv
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import hours_mask, ema

NAME = "vol_absorb_maker_bias"

SIM = dict(maxhold=180, dollars_per_point=1.0, commission=0.07, cooldown=12)

# --- tunable params (runner sweeps these +/-30%) ---
W_VOL = 60          # rolling-vol-mean window (5 min of 5s bars)
VSPIKE = 2.0        # volume spike: vol >= VSPIKE * rolling mean
LOOKBACK = 150      # bars defining the liquidity extreme (~12.5 min)
EMA_TREND = 600     # HTF-bias EMA on mid (~50 min)
LEVOFF = 0.20       # maker limit offset beyond the level (pts)
SL_PTS = 1.6
TP_PTS = 1.2
TTL = 18            # bars the limit stays live before cancel
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active hours (UTC)


def generate(b: Bars) -> Signals:
    n = b.n
    vmean = np.full(n, np.nan)
    if n > W_VOL:
        vmean[W_VOL:] = swv(b.vol[:-1].astype(np.float64), W_VOL).mean(axis=1)
    spike = (b.vol >= VSPIKE * vmean) & np.isfinite(vmean)

    rmax = roll_max(b.mid, LOOKBACK)
    rmin = roll_min(b.mid, LOOKBACK)
    es = ema(b.mid, EMA_TREND)
    sess = hours_mask(b, SESSION_HOURS)

    # resistance absorption -> fade SHORT, only in a downtrend (fade INTO HTF bias)
    up = spike & sess & (b.bh >= rmax) & np.isfinite(rmax) & (b.mid < es)
    # support absorption -> fade LONG, only in an uptrend
    dn = spike & sess & (b.bl <= rmin) & np.isfinite(rmin) & (b.mid > es)

    iu = np.where(up)[0]
    il = np.where(dn)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    level = np.concatenate([rmax[iu] + LEVOFF, rmin[il] - LEVOFF])
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    m = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(m, int),                 # maker limit entry
        level=level,
        sl_pts=np.full(m, SL_PTS),
        tp_pts=np.full(m, TP_PTS),
        ttl=np.full(m, TTL),
    )
