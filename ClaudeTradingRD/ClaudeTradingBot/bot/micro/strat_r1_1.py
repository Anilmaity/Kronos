"""Asian-range AMD — London sweep-and-reversion of the Asian session range.

CONCEPT (accumulation -> manipulation -> distribution):
  1. ACCUMULATION: 00:00-07:00 UTC the market builds the "Asian range"
     [asia_lo, asia_hi] on mid prices. After 07:00 the range is FIXED & known
     (fully causal -- we only ever act during/after London).
  2. MANIPULATION: early London (07:00-11:00 UTC) runs liquidity resting just
     beyond the Asian high/low (a sweep / stop-hunt wick).
  3. DISTRIBUTION: price REVERTS back inside the range. We fade the sweep:
       - sweep of asia HIGH + close back inside  -> SHORT
       - sweep of asia LOW  + close back inside   -> LONG

  The naive "took out prior high" trigger has no edge (SCOUT_FINDINGS). The
  filters that create excursion asymmetry here:
    * the level is a GENUINE resting-liquidity pool (a full Asian session H/L),
      not a rolling-N extreme;
    * the sweep must RECLAIM the level on the same bar (a rejection), so we only
      act on manipulation that already failed, not on a clean trend breakout;
    * shallow-penetration filter (MAX_PEN) discards deep breaks = real expansion;
    * one trade per side per day -> 3-25 trades/day across both sides, fading the
      first sweep only.
  Stop sits just beyond the sweep wick; target is an R-multiple back into range.

CONTRACT: generate(b)->Signals (causal), SIM dict, NAME.
"""
import numpy as np
from bot.micro.engine import Bars, Signals
from bot.micro.features import ema

NAME = "asian_amd"

SIM = dict(maxhold=300, dollars_per_point=1.0, commission=0.07, cooldown=12)

# ---- tunable params (robustness-checked +/-30%) ----
ASIA_S, ASIA_E = 0, 7          # Asian session UTC window [start,end)
ENTRY_HOURS = (7, 8, 9, 10, 11)  # London manipulation window (UTC hours)
MIN_REVERT = 1.0               # close must reclaim >= this many pts inside the level
MAX_PEN = 5.0                  # reject sweeps whose wick pierces > this (= real expansion)
BUFFER = 1.0                   # stop sits this far beyond the sweep wick
RR = 2.0                       # target = RR * stop distance
MAX_SL = 6.0                   # cap stop distance (pts)
MIN_RANGE, MAX_RANGE = 5.0, 30.0   # only trade days with a "normal" Asian range
BIAS_P = 1440                  # slow EMA (~2h) defining higher-TF bias direction


def generate(b: Bars) -> Signals:
    n = b.n
    mid_h = (b.ah + b.bh) * 0.5
    mid_l = (b.al + b.bl) * 0.5

    # ---- per-bar Asian-session H/L for that bar's day (causal: used only after 07:00) ----
    asia_hi = np.full(n, np.nan)
    asia_lo = np.full(n, np.nan)
    for dd in np.unique(b.day):
        idx = np.where(b.day == dd)[0]
        hod = b.hod[idx]
        am = idx[(hod >= ASIA_S) & (hod < ASIA_E)]
        if len(am) < 100:        # require a real Asian session
            continue
        asia_hi[idx] = mid_h[am].max()
        asia_lo[idx] = mid_l[am].min()

    rng = asia_hi - asia_lo
    sess = np.isin(b.hod, np.asarray(ENTRY_HOURS))
    base = np.isfinite(asia_hi) & sess & (rng >= MIN_RANGE) & (rng <= MAX_RANGE)

    # higher-TF bias: only fade a sweep when the reversion runs WITH the larger
    # trend (counter-trend liquidity grab -> resume). bias_up => trade LOW-sweeps
    # (judas low then rally); bias_dn => trade HIGH-sweeps.
    bias = b.mid - ema(b.mid, BIAS_P)
    bias_up = bias > 0
    bias_dn = bias < 0

    pen_hi = b.ah - asia_hi      # how far the ask wick pierced above
    pen_lo = asia_lo - b.bl
    short_ok = (base & bias_dn & (b.ah > asia_hi)
                & (b.bc < asia_hi - MIN_REVERT) & (pen_hi <= MAX_PEN))
    long_ok = (base & bias_up & (b.bl < asia_lo)
               & (b.ac > asia_lo + MIN_REVERT) & (pen_lo <= MAX_PEN))

    # ---- first sweep per side per day ----
    def first_per_day(mask):
        ii = np.where(mask)[0]
        if len(ii) == 0:
            return ii
        keep = []
        seen = set()
        for i in ii:
            d = b.day[i]
            if d not in seen:
                seen.add(d)
                keep.append(i)
        return np.asarray(keep, np.int64)

    is_short = first_per_day(short_ok)
    is_long = first_per_day(long_ok)

    i = np.concatenate([is_short, is_long]).astype(np.int64)
    side = np.concatenate([-np.ones(len(is_short), int), np.ones(len(is_long), int)])

    # ---- dynamic stop just beyond the sweep wick, target = RR*stop ----
    sl_pts = np.empty(len(i))
    tp_pts = np.empty(len(i))
    for k, (ix, sd) in enumerate(zip(i, side)):
        if sd < 0:   # short: entry ~ bid close, stop above ask wick
            entry_ref = b.bc[ix]
            d = (b.ah[ix] - entry_ref) + BUFFER
        else:        # long: entry ~ ask close, stop below bid wick
            entry_ref = b.ac[ix]
            d = (entry_ref - b.bl[ix]) + BUFFER
        d = min(max(d, 1.5), MAX_SL)
        sl_pts[k] = d
        tp_pts[k] = RR * d

    o = np.argsort(i, kind="stable")
    i, side, sl_pts, tp_pts = i[o], side[o], sl_pts[o], tp_pts[o]
    m = len(i)
    return Signals(
        i=i, side=side,
        kind=np.zeros(m, int),     # market entry next bar (TAKER, deployable)
        level=np.zeros(m),
        sl_pts=sl_pts,
        tp_pts=tp_pts,
    )
