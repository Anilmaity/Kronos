"""Volume-spike ABSORPTION fade (pinned-bar variant), maker entry.

CONCEPT (assigned): a 5s bar whose tick-volume is >> its rolling mean but which
FAILS TO EXTEND price (absorption) sitting at a liquidity level -> fade the
exhaustion.

WHY THIS VARIANT IS DIFFERENT FROM THE DEAD ENDS
The prior absorption attempts (vol_absorption_fade pf 0.42, vol_absorb_maker_bias
pf 0.288) defined "absorption" as a bar that POKES beyond a rolling extreme and
closes back inside (a sweep-and-reject). Measured here, that trigger has a
SYMMETRIC forward excursion (MFE ~= -MAE, final drift ~+0.26pt) which is below the
0.66pt spread floor -> every taker AND maker bracket loses (pf 0.38-0.64).

This variant uses the *literal* microstructure meaning of absorption instead:
  ABSORPTION = a volume SPIKE (vol > K * rolling-mean) that produces a TINY price
  move (mid-range < SMALL_F * ATR) -- i.e. heavy participation that the market
  PINS in place -- occurring right AT a recent liquidity level (within NEAR_F*ATR
  of the rolling N-bar high or low). Buyers absorbed at resistance -> short;
  sellers absorbed at support -> long.
Measured on train (2024-01..2025-07) this pinned definition DOES show genuine
asymmetry (support-absorption longs: MFE_med 5.4 vs MAE_med -2.5, win-frac 0.64).

EXECUTION: MAKER. A passive limit is posted at the absorption bar's mid/close so a
fill earns ~half the spread; that spread capture is what lifts the thin asymmetry
from break-even to a small positive. (NOTE on deployability: the user's FundingPips
MT5 account is taker-only, so this maker line is RESEARCH-valuable but not directly
deployable there; the taker version of the same trigger is ~break-even, pf ~1.0.)

HONEST RESULT: this is a cost-floor edge, not a pass. The asymmetry is real but
RARE -- the high-quality pinned-absorption events are ~1-1.5/day, below the 3-25/day
target, and pushing frequency up (looser SMALL_F/K) re-introduces the low-quality
events and collapses pf back below 1.0 (the classic frequency-vs-edge wall). So the
deliverable is: pinned-volume-absorption has a small, real, maker-only mean-reversion
edge on XAU 5s that barely clears the spread, at a frequency too low to meet the
trade-count/day mandate. Reported with the runner JSON below.

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only (vol-mean, ATR, rolling
extremes all use bars < i; the trigger reads only bar i's own OHLCV at its close).
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view as swv
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask

NAME = "vol_absorb_pinned_maker"

SIM = dict(maxhold=360, dollars_per_point=1.0, commission=0.07, cooldown=24)

# --- tunable params (runner sweeps vary these +/-30%) ---
VOL_W   = 720          # rolling window for the volume baseline (~1h of 5s bars)
VOL_K   = 3.5          # spike threshold: vol > VOL_K * rolling-mean(vol)
LVL_N   = 120          # bars defining the liquidity level (rolling hi/lo, ~10 min)
SMALL_F = 0.6          # "pinned": mid-range of the spike bar < SMALL_F * ATR(14)
NEAR_F  = 0.8          # bar must sit within NEAR_F * ATR of the rolling hi/lo
TP_PTS  = 6.0          # target (captures the asymmetric MFE)
SL_PTS  = 3.0          # stop (beyond the typical adverse excursion)
TTL     = 30           # bars the passive limit stays live (~2.5 min)
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15, 16)   # London + NY active (UTC)


def generate(b: Bars) -> Signals:
    n = b.n
    mid = b.mid
    vol = b.vol.astype(np.float64)

    # causal rolling-mean volume baseline (uses bars strictly before i)
    volmean = np.full(n, np.nan)
    if n > VOL_W:
        volmean[VOL_W:] = swv(vol[:-1], VOL_W).mean(axis=1)

    A = atr(b, 14)
    rmax = roll_max(mid, LVL_N)
    rmin = roll_min(mid, LVL_N)
    sess = hours_mask(b, SESSION_HOURS)

    # mid range of the current bar (its own OHLC -> causal at close)
    mid_rng = (b.ah + b.bh) * 0.5 - (b.al + b.bl) * 0.5

    spike = vol > VOL_K * volmean
    pinned = mid_rng < SMALL_F * A
    near_hi = (rmax - mid) < NEAR_F * A
    near_lo = (mid - rmin) < NEAR_F * A

    # absorption at resistance -> fade SHORT ; absorption at support -> fade LONG
    abs_hi = spike & pinned & near_hi & sess & np.isfinite(rmax)
    abs_lo = spike & pinned & near_lo & sess & np.isfinite(rmin)

    iu = np.where(abs_hi)[0]
    il = np.where(abs_lo)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    o = np.argsort(i, kind="stable")
    i, side = i[o], side[o]
    nn = len(i)

    # MAKER: passive limit at the absorption bar's close (earns ~half spread on fill)
    level = b.bc[i]
    return Signals(
        i=i, side=side,
        kind=np.ones(nn, int),                 # 1 = limit (maker)
        level=level,
        sl_pts=np.full(nn, SL_PTS),
        tp_pts=np.full(nn, TP_PTS),
        ttl=np.full(nn, TTL, np.int64),
    )
