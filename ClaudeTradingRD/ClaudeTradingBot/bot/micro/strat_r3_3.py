"""Liquidity-sweep reversal (assigned concept) — EQUAL-LEVEL CLUSTER + HTF-bias
MAKER fade. Distinct from the prior dead ends (swept_swing_fade, swing_sweep_fade_
filtered, eqhl_raid*) which faded every confirmed swing with a taker market entry.

DIFFERENT DIRECTION TRIED HERE
  1. LEVEL QUALITY = a multi-touch EQUAL-LEVEL CLUSTER. A confirmed M5 swing only
     counts as resting liquidity if >=1 EARLIER confirmed swing of the same type
     sits within TOL points of it (so >=2 equal highs / equal lows). This is the
     "equal-highs cluster" the scout/assignment flags as the highest-quality pool,
     not just any single fractal extreme.
  2. HTF BIAS ALIGNMENT = only fade a swept LOW when the M5 EMA(10/40) bias is UP
     (buy the stop-hunt dip in an uptrend) and a swept HIGH when bias is DOWN — a
     discount/premium retracement entry, not a blind counter-trend catch.
  3. MAKER (limit) ENTRY resting AT the cluster level, so the fill earns the spread
     instead of paying it (kind=1). The fade target is modest; stop sits beyond the
     wick.

CAUSALITY
  - M5 swing at HTF bar j is centred (SWING_K each side) -> usable only after bar
    j+SWING_K closes; its level is attached to that confirmation bar's last S5 index
    and read with searchsorted 'left' (strictly earlier bars only).
  - Cluster count for a level uses only EARLIER confirmed swings (prefix scan).
  - HTF EMA bias for S5 bar i uses the last HTF bar whose close S5-index <= i.
  - ATR / sessions are the decision bar's own (causal). Entry is a limit filled on
    a later bar by the engine. No future bar is indexed in generate().

HONEST RESULT (refutation, reported per GOAL.md)
  This still does NOT beat the cost floor. On the official split
  (train 2024-01..2025-07, OOS 2025-08..2026-06) the shipped config lands ~53-56%
  WR but PF ~0.55-0.72, net NEGATIVE, t/d ~3. Across an internal scan (taker vs
  maker; tp 1..8 / sl 2..4; trailing & break-even exits; cluster>=1 vs >=2; bias on
  vs off) EVERY OOS cell was negative. The equal-level + bias + maker combination
  raises win rate but the post-sweep reversion magnitude remains smaller than the
  ~0.66pt bid/ask spread, so the maker fill cannot recover it and a wider target
  loses the win rate. Conclusion matches the project's standing finding: the XAU S5
  liquidity-sweep FADE is a cost-dominated non-edge for a deployable (taker) account
  and only marginally monetisable, at best break-even, as a thin maker line.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import resample, swings, hours_mask, ema

NAME = "eqlvl_cluster_bias_maker_fade"

SIM = dict(maxhold=360, dollars_per_point=1.0, commission=0.07, cooldown=18)

# --- tunable params (runner/sweeps vary +-30%) ---
HTF_SECONDS = 300            # M5 structure timeframe for swings + bias
SWING_K = 2                  # confirmed fractal half-width
CLUSTER_TOL = 0.5            # pts: two swings within this are an "equal level"
MIN_CLUSTER = 2              # require >=2 equal swings (>=1 earlier touch) to trade
EMA_FAST, EMA_SLOW = 10, 40  # HTF EMA bias (on M5 close)
USE_BIAS = True              # only fade a sweep INTO the higher-TF direction
PEN_MIN = 0.15               # sweep wick must poke >= this beyond the level
PEN_MAX = 2.0                # ...but skip runaway breakouts deeper than this
MIN_REVERT = 0.30            # close must reclaim this many pts back inside the level
ATR_LO, ATR_HI = 0.20, 1.6   # ATR(14) band (pts)
AGE_MIN = 6                  # level at least this many S5 bars old (post-confirm)
AGE_MAX = 6000               # ...and fresher than ~8h
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15, 16)  # London + NY (UTC)
SL_PTS = 4.0
TP_PTS = 2.0
TTL = 60                     # bars the resting limit stays live


def _confirmed_cluster_levels(b: Bars):
    """For every S5 bar: nearest confirmed M5 swing high/low level whose
    confirmation closed STRICTLY before i, that level's equal-level cluster count
    (earlier same-type swings within CLUSTER_TOL), and its age in S5 bars."""
    m = resample(b, HTF_SECONDS)
    h, l, s5i, c = m["h"], m["l"], m["s5_idx"], m["c"]
    K = len(h)
    sh, sl = swings(h, l, SWING_K)

    # HTF EMA bias mapped to S5 (last HTF bar with close-index <= i)
    ef, es = ema(c, EMA_FAST), ema(c, EMA_SLOW)
    hbias = np.where(ef > es, 1, -1)
    s5_bias = np.zeros(b.n, np.int8)
    pos = np.searchsorted(s5i, np.arange(b.n), side="right") - 1
    g = pos >= 0
    s5_bias[g] = hbias[pos[g]]

    def build(mask, vals):
        js = np.where(mask)[0]
        js = js[js + SWING_K < K]
        conf = s5i[js + SWING_K]
        lvl = vals[js]
        o = np.argsort(conf, kind="stable")
        conf, lvl = conf[o], lvl[o]
        cc = np.zeros(len(lvl), np.int32)
        for q in range(1, len(lvl)):
            cc[q] = int(np.sum(np.abs(lvl[:q] - lvl[q]) <= CLUSTER_TOL))
        idx = np.arange(b.n)
        p = np.searchsorted(conf, idx, side="left") - 1
        out_lvl = np.full(b.n, np.nan)
        out_cc = np.zeros(b.n, np.int32)
        out_age = np.full(b.n, -1, np.int64)
        ok = p >= 0
        out_lvl[ok] = lvl[p[ok]]
        out_cc[ok] = cc[p[ok]]
        out_age[ok] = idx[ok] - conf[p[ok]]
        return out_lvl, out_cc, out_age

    shl, shc, sha = build(sh, h)
    sll, slc, sla = build(sl, l)
    return s5_bias, shl, shc, sha, sll, slc, sla


def generate(b: Bars) -> Signals:
    A = atr(b, 14)
    bias, shl, shc, sha, sll, slc, sla = _confirmed_cluster_levels(b)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)
    bias_up = (bias > 0) if USE_BIAS else np.ones(b.n, bool)
    bias_dn = (bias < 0) if USE_BIAS else np.ones(b.n, bool)

    pen_up = b.ah - shl
    sweep_up = (np.isfinite(shl) & (shc >= MIN_CLUSTER)
                & (pen_up >= PEN_MIN) & (pen_up <= PEN_MAX)
                & (b.bc < shl - MIN_REVERT)
                & (sha >= AGE_MIN) & (sha <= AGE_MAX)
                & sess & volok & bias_dn)
    pen_dn = sll - b.al
    sweep_dn = (np.isfinite(sll) & (slc >= MIN_CLUSTER)
                & (pen_dn >= PEN_MIN) & (pen_dn <= PEN_MAX)
                & (b.bc > sll + MIN_REVERT)
                & (sla >= AGE_MIN) & (sla <= AGE_MAX)
                & sess & volok & bias_up)

    iu = np.where(sweep_up)[0]
    il = np.where(sweep_dn)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    level = np.concatenate([shl[iu], sll[il]])   # maker: rest at the cluster level
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(n, int),                    # limit (maker) entry at the level
        level=level,
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, TP_PTS),
        ttl=np.full(n, TTL, np.int64),
    )
