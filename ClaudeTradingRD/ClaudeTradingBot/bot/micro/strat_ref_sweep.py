"""REFERENCE STRATEGY + TEMPLATE — Filtered Liquidity Sweep Reversal.

Copy this file to make a new candidate. Edit `generate()` and `SIM`. The naive
unfiltered version of this idea loses -$10k/month (see GOAL.md). This adds filters
to isolate the rare high-quality sweep: session, volatility band, and a minimum
reversion of the wick. Demonstrates the contract; not guaranteed to pass.

CONTRACT:
  generate(b: Bars) -> Signals    # causal: only use info up to bar i's close
  SIM = dict(...)                 # forwarded to engine.simulate
  NAME = "label"
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask

NAME = "ref_filtered_sweep"

# simulate() kwargs — exits are mostly defined here via Signals sl/tp + these
SIM = dict(maxhold=180, dollars_per_point=1.0, commission=0.07, cooldown=12)

# --- tunable params (the runner / sweeps vary these ±30%) ---
LOOKBACK = 30        # bars defining the liquidity level
MIN_REVERT = 0.30    # bar must close back this many pts inside the swept level
ATR_LO, ATR_HI = 0.30, 1.20   # only trade when ATR(14) in this band (pts)
SL_PTS = 2.0
TP_PTS = 3.0
SESSION_HOURS = (7, 8, 9, 12, 13, 14, 15)   # London + NY active hours (UTC)


def generate(b: Bars) -> Signals:
    A = atr(b, 14)
    rmax = roll_max(b.mid, LOOKBACK)
    rmin = roll_min(b.mid, LOOKBACK)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)

    # sweep up = took out prior high on the wick, closed back below by >= MIN_REVERT
    sweep_up = (b.ah > rmax) & (b.bc < rmax - MIN_REVERT) & np.isfinite(rmax) & sess & volok
    sweep_dn = (b.al < rmin) & (b.bc > rmin + MIN_REVERT) & np.isfinite(rmin) & sess & volok

    iu = np.where(sweep_up)[0]
    il = np.where(sweep_dn)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    o = np.argsort(i, kind="stable")
    i, side = i[o], side[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.zeros(n, int),                 # market entry next bar
        level=np.zeros(n),
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, TP_PTS),
    )
