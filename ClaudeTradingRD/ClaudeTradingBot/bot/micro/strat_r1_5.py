"""Liquidity-sweep reversal (fade the stop-hunt) — heavily filtered.

CONCEPT (assigned): price wicks beyond a recent swing high/low (a stop hunt on
resting liquidity), then closes back inside; fade it. The whole game is FILTERING
to high-quality sweeps so the post-sweep reversion is asymmetric (favorable >>
adverse), enough to clear the spread.

WHY THIS SHOULD HAVE EDGE WHERE THE NAIVE TRIGGER DOES NOT (scout findings):
  * Level = a CONFIRMED M1 fractal swing that actually formed and held — genuine
    resting liquidity — NOT every rolling-N extreme (those just track a trend).
  * Sweep must PENETRATE the level (displacement wick) AND CLOSE BACK INSIDE by a
    margin (decisive rejection / reclaim).
  * Volume spike on the sweep bar (absorption — someone fading the hunt).
  * Session filter (London + NY only); ATR band (skip dead / chaotic regimes).
  * Level freshness window (liquidity is freshest when recently built).

Causality: M1 swing at bar j is centered (k each side) -> only "known" once bar
j+k has closed. We map that confirmation to its last S5 index and only allow the
level to be used on STRICTLY LATER S5 bars (searchsorted 'left'). roll_max/min and
the cumsum vol-mean are causal (exclude current bar where it matters). We act at
bar i using only info up to close[i]; entry is next-bar market (taker).

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import resample, swings, hours_mask, ema

NAME = "swept_swing_fade"

SIM = dict(maxhold=180, dollars_per_point=1.0, commission=0.07, cooldown=24)

# --- tunable params (runner sweeps vary ±30%) ---
M1_SEC = 60          # resample TF for swing levels
SWING_K = 3          # fractal half-width (bars each side); larger = stronger swing
MIN_REVERT = 0.30    # close must reclaim this many pts back inside the level
PEN_MIN = 0.15       # sweep wick must poke >= this far beyond the level
PEN_MAX = 2.50       # ...but not a runaway breakout (skip if poke deeper than this)
VOL_W = 60           # bars for the rolling mean volume (5 min)
VOL_MULT = 1.8       # sweep bar volume >= this * rolling mean (absorption spike)
ATR_LO, ATR_HI = 0.18, 1.40
AGE_MIN = 6          # level must be at least this many S5 bars old (post-confirm)
AGE_MAX = 4000       # ...and not staler than this (~5.5 h)
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15, 16)  # London + NY (UTC)
EMA_BIAS = 1500      # long EMA on mid (~125 min) for HTF bias gate
BIAS_BAND = 0.10     # mid must be this far the right side of EMA (pts) to count
USE_BIAS = False     # bias gate measured to NOT help (see module footer)
SL_PTS = 2.5         # wide stop beyond the swept wick
TP_PTS = 1.0         # small reversion target = highest realizable WR config found


def _last_confirmed_levels(b: Bars):
    """For every S5 bar i, the price of the most recent CONFIRMED M1 swing high
    and swing low whose confirmation bar closed STRICTLY BEFORE i, plus the S5
    index of that confirmation (for age). nan / -1 where none yet."""
    m = resample(b, M1_SEC)
    h, l, s5_idx = m["h"], m["l"], m["s5_idx"]
    sh, sl = swings(h, l, SWING_K)
    K = len(h)

    def build(mask, vals):
        js = np.where(mask)[0]
        js = js[js + SWING_K < K]               # confirmation bar must exist
        conf = s5_idx[js + SWING_K]             # S5 index where swing is confirmed
        lvl = vals[js]
        o = np.argsort(conf, kind="stable")
        conf, lvl = conf[o], lvl[o]
        idx = np.arange(b.n)
        pos = np.searchsorted(conf, idx, side="left") - 1  # last conf strictly < i
        out_lvl = np.full(b.n, np.nan)
        out_age = np.full(b.n, -1, np.int64)
        ok = pos >= 0
        out_lvl[ok] = lvl[pos[ok]]
        out_age[ok] = idx[ok] - conf[pos[ok]]
        return out_lvl, out_age

    shl, sha = build(sh, h)
    sll, sla = build(sl, l)
    return shl, sha, sll, sla


def _roll_mean_vol(vol, w):
    """Causal mean of the prior w bars' volume (excludes current bar)."""
    v = vol.astype(np.float64)
    c = np.concatenate(([0.0], np.cumsum(v)))
    out = np.full(len(v), np.nan)
    if len(v) > w:
        out[w:] = (c[w:-1] - c[:-w - 1]) / w
    return out


def generate(b: Bars) -> Signals:
    A = atr(b, 14)
    shl, sha, sll, sla = _last_confirmed_levels(b)
    vmean = _roll_mean_vol(b.vol, VOL_W)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)
    volspike = b.vol.astype(np.float64) >= VOL_MULT * vmean

    # HTF bias gate: a sweep is a high-quality reversal only when it grabs
    # liquidity AGAINST the higher-TF direction (manipulation leg of AMD).
    # bias bear -> fade sweep-UPs (short with trend); bias bull -> fade sweep-DOWNs.
    eb = ema(b.mid, EMA_BIAS)
    bias_bear = (b.mid < eb - BIAS_BAND) if USE_BIAS else np.ones(b.n, bool)
    bias_bull = (b.mid > eb + BIAS_BAND) if USE_BIAS else np.ones(b.n, bool)

    # --- sweep UP (took out a swing high), closed back below -> fade SHORT ---
    pen_up = b.ah - shl
    sweep_up = (
        np.isfinite(shl)
        & (pen_up >= PEN_MIN) & (pen_up <= PEN_MAX)
        & (b.bc < shl - MIN_REVERT)
        & (sha >= AGE_MIN) & (sha <= AGE_MAX)
        & sess & volok & volspike & bias_bear
    )
    # --- sweep DOWN (took out a swing low), closed back above -> fade LONG ---
    pen_dn = sll - b.al
    sweep_dn = (
        np.isfinite(sll)
        & (pen_dn >= PEN_MIN) & (pen_dn <= PEN_MAX)
        & (b.bc > sll + MIN_REVERT)
        & (sla >= AGE_MIN) & (sla <= AGE_MAX)
        & sess & volok & volspike & bias_bull
    )

    iu = np.where(sweep_up)[0]
    il = np.where(sweep_dn)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    o = np.argsort(i, kind="stable")
    i, side = i[o], side[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.zeros(n, int),
        level=np.zeros(n),
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, TP_PTS),
    )


# ----------------------------------------------------------------------------
# MEASURED FINDINGS (train 2024-01..2025-07, OOS 2025-08..2026-06) — HONEST
# ----------------------------------------------------------------------------
# This concept does NOT clear the cost floor on XAU S5. Evidence from the runs:
#   * Final taker config (above): WR ~48-49%, PF 0.35-0.39, net NEGATIVE, and
#     PF collapses to 0.14 under the 1.5x stress pass. FAILS the acceptance bar.
#   * Mid-path (spread-free) the sweep has a FAINT structural edge: P(hit +1.0pt
#     before -2.5pt) ~= 0.74, EV ~ +0.08pt/trade. But the median bid/ask spread
#     (~0.32-0.66pt) is LARGER than that edge, so it is unrealizable as a taker:
#     the real-fill WR halves from 74% (mid) to ~49% (bid/ask).
#   * HTF-EMA bias gate (only fade against the larger trend): no WR improvement
#     (stuck ~30-49%), just imbalanced the sides. Did not help -> USE_BIAS=False.
#   * MAKER entry (limit retest of the swept swing level, which WOULD earn the
#     spread) is ADVERSELY SELECTED: the limit fills precisely when price rallies
#     back through the level because the breakout is succeeding -> WR ~18-23%,
#     PF 0.27-0.39. A shallow spread-earning limit fared no better (PF 0.37-0.47).
#   * Tightening filters (reversion 0.3->1.0, vol-spike 1.8->3.0x, penetration
#     band) cut frequency from ~6/day to ~1/day but left WR ~48% / PF ~0.4 flat.
# CONCLUSION: the liquidity-sweep reversal FADE is real microstructure but its
# reversion magnitude is below the spread on this instrument/timeframe. It is not
# taker-deployable, and the natural maker entry that would monetise it is
# adversely selected. This reproduces the project's "mean-rev edge sits at the
# cost floor" finding. Reported as a negative result with evidence, per GOAL.md.
