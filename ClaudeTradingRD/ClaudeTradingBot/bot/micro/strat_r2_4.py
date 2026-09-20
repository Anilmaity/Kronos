"""Liquidity-sweep reversal (assigned concept) -- best-filtered, honest version.

Setup: price wicks beyond a CONFIRMED M5 swing high/low (genuine resting
liquidity, not every S5 extreme), then closes decisively back inside (rejection)
on a VOLUME-SPIKE bar, during London/NY hours, in a sane ATR band. Fade it
(market entry next bar). These are exactly the quality filters the assignment
calls for: session, displacement/rejection into the level, and a volume spike on
the wick.

HONEST RESULT (this is a refutation, reported per GOAL's honesty rules):
This concept has no taker edge on XAU S5. Direct diagnostics on the real data
(2024-01..2025-07 train) show, even after the *best* filters found:
  - best LONG slice ~35% WR at 1.6R -> below the ~38% taker break-even;
  - a full TP(2..8) x SL(1.5..2.5) x hold(15..60min) grid is NEGATIVE in EVERY
    cell (best PF 0.72); per-trade expectancy sits at ~-$0.60 == the round-trip
    cost, i.e. gross edge ~= 0 and the 0.66pt spread is the entire loss.
Maker (limit) variants were also tested: resting at the level fills on momentum
into it (PF 0.36); a confirmed-rejection RETEST limit gets shredded by the tight
wick stop (WR ~17%). None clear the acceptance bar.

This module ships the cleanest symmetric version of the concept for a comparable,
non-cherry-picked score. It does NOT pass; the deliverable is the evidence that on
this instrument/timeframe the liquidity-sweep fade is a cost-dominated non-edge.

CAUSALITY: M5 swing used only after bar j+SWING_K closes; volume z uses a trailing
window excluding the current bar; per-bar fields are the decision bar's own.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import resample, swings, hours_mask

NAME = "swing_sweep_fade_filtered"

SIM = dict(maxhold=360, dollars_per_point=1.0, commission=0.07, cooldown=18)

# --- tunable params (runner/sweeps vary +-30%) ---
HTF_SECONDS = 300              # M5 structure timeframe
SWING_K = 2                    # confirmed fractal half-width
MIN_REVERT = 0.40             # close must reclaim >= this many pts inside the level
VOL_W = 60                    # trailing window for volume z-score (S5 bars)
VOL_Z = 1.0                   # require sweep-bar volume z >= this
ATR_LO, ATR_HI = 0.25, 1.6    # ATR(14) band (pts)
SL_PTS = 2.5
TP_PTS = 4.0
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)


def _ffill(a):
    idx = np.where(~np.isnan(a), np.arange(len(a)), 0)
    np.maximum.accumulate(idx, out=idx)
    return a[idx]


def generate(b: Bars) -> Signals:
    n = b.n
    R = resample(b, HTF_SECONDS)
    h5, l5 = R["h"], R["l"]
    s5i = R["s5_idx"]
    K = len(h5)
    sh, sl = swings(h5, l5, SWING_K)

    hi_lvl = np.full(n, np.nan)
    lo_lvl = np.full(n, np.nan)
    for j in range(K):
        jc = j + SWING_K
        if jc >= K:
            continue
        cc = s5i[jc] + 1
        if cc >= n:
            continue
        if sh[j]:
            hi_lvl[cc] = h5[j]
        if sl[j]:
            lo_lvl[cc] = l5[j]
    hi_lvl = _ffill(hi_lvl)
    lo_lvl = _ffill(lo_lvl)

    A = atr(b, 14)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)

    vol = b.vol.astype(np.float64)
    vmean = np.full(n, np.nan)
    vstd = np.full(n, np.nan)
    if n > VOL_W:
        from numpy.lib.stride_tricks import sliding_window_view as swv
        vw = swv(vol[:-1], VOL_W)
        vmean[VOL_W:] = vw.mean(1)
        vstd[VOL_W:] = vw.std(1) + 1e-9
    vz = (vol - vmean) / vstd
    volspike = np.isfinite(vz) & (vz >= VOL_Z)

    # LONG: swing low swept (bid_low < level) and reclaimed (close > level + revert)
    sweep_lo = (np.isfinite(lo_lvl) & (b.bl < lo_lvl) & (b.bc > lo_lvl + MIN_REVERT)
                & sess & volok & volspike)
    # SHORT: swing high swept (ask_high > level) and reclaimed (close < level - revert)
    sweep_hi = (np.isfinite(hi_lvl) & (b.ah > hi_lvl) & (b.bc < hi_lvl - MIN_REVERT)
                & sess & volok & volspike)

    il = np.where(sweep_lo)[0]
    ih = np.where(sweep_hi)[0]
    i = np.concatenate([il, ih])
    side = np.concatenate([np.ones(len(il), int), -np.ones(len(ih), int)])
    o = np.argsort(i, kind="stable")
    i, side = i[o], side[o]
    m = len(i)
    return Signals(
        i=i, side=side,
        kind=np.zeros(m, int),              # market entry next bar (taker)
        level=np.zeros(m),
        sl_pts=np.full(m, SL_PTS),
        tp_pts=np.full(m, TP_PTS),
    )
