"""Equal-highs/lows raid -> bias-aligned maker fade at the liquidity pool.

ASSIGNED CONCEPT: a cluster of *equal* highs (or lows) is genuine resting liquidity --
stops parked just beyond it. Price raids the cluster to take that liquidity, then
reverses. Trade the raid-and-reverse.

HOW THIS DIFFERS from the eqhl_raid / eqhl_raid_maker dead ends:
  1. GENUINE POOL, not a lone rolling extreme. A pool exists only when >=2 *confirmed
     M1 swing* highs sit within TOL points of each other, separated by >= MIN_SEP min
     and <= PAIR_WIN min (a real double/triple top that HELD and was retested).
     swings() is centered (k bars) so a level is referenced only after it confirms -> causal.
  2. BIAS GATE. A slow causal EMA sets daily direction; we only fade a HIGH-pool raid
     when bias is DOWN (the rally into the highs is a counter-trend grab we fade short
     WITH the downtrend) and a LOW-pool raid only when bias is UP. Scout finding #2:
     the excursion asymmetry only appears when the raid runs AGAINST bias.
  3. MAKER limit resting AT the pool (earns the ~0.66pt spread instead of paying it).

HONEST RESULT -- THIS DOES NOT CLEAR THE BAR (reported as evidence, per GOAL.md):
  Equal-highs/lows raids on XAU 5s have no live edge. I tested four genuinely distinct
  constructions of this concept and every one lands at profit-factor ~0.55-0.68, net
  negative on OOS, worse under 1.5x stress:
    * resting-limit maker fade (this file): OOS pf 0.679, WR 47.9%, net -$4,170, 22/day
    * reclaim-retest maker fade (rejection-confirmed): OOS pf 0.610
    * breakout-retest continuation (pool flips to support): OOS pf 0.619, WR 29.6%
    * selective taker reclaim fade + session + volume-spike gate: OOS pf 0.602, WR 36.5%
  Two failure mechanisms, both fatal: (a) a resting fade limit is adversely selected --
  it fills precisely on the strong raids that blow through, not the weak ones that
  reverse; (b) waiting for a confirmed reclaim and entering taker pays the spread to
  chase a reversion that is ~symmetric (scout finding #2). Selectivity (down to 2.6
  trades/day with bias+session+absorption gates) shrinks the loss but never flips the
  sign. This reproduces and extends the two prior eqhl dead ends: the equal-highs/lows
  raid is noise relative to the 0.66pt spread, taker OR maker, fade OR continuation.

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only; maker-only (research-grade).
"""
import numpy as np
from bot.micro.engine import Bars, Signals
from bot.micro.features import resample, swings, ema

NAME = "eqhl_pool_bias_maker"

SIM = dict(maxhold=300, dollars_per_point=1.0, commission=0.07, cooldown=24)

# --- tunable params (runner sweeps +-30%) ---
M1_SEC      = 60      # resample seconds for swing structure
K           = 2       # swing half-window (confirmed K bars later)
TOL         = 1.1     # max pt gap between two swings to count as an "equal" cluster
MIN_SEP_MIN = 6.0     # the two swings must be >= this far apart in time (real retest)
PAIR_WIN_MIN= 75.0    # ...and <= this far apart (pool still fresh)
EMA_BIAS    = 5760    # slow EMA for daily bias (~8h of 5s bars)
SL_PTS      = 4.5     # stop beyond the pool (covers the liquidity poke)
TP_PTS      = 3.3     # reversion target off the pool
TTL         = 300     # bars the resting limit stays live (~25 min) to catch the raid


def generate(b: Bars) -> Signals:
    Eb = ema(b.mid, EMA_BIAS)
    R = resample(b, M1_SEC)
    h, l, s5idx = R["h"], R["l"], R["s5_idx"]
    nM = len(h)
    sh, sl = swings(h, l, K)

    sig_i, sig_side, sig_level = [], [], []

    def scan(swing_mask, levels, want_high):
        # want_high True -> high pool -> short on DOWN bias ; else low pool -> long on UP bias
        recent = []  # (level, conf_s5_idx)
        for j in np.where(swing_mask)[0]:
            conf = j + K
            if conf >= nM:
                continue
            ct = int(s5idx[conf])
            lvl = float(levels[j])
            t_now = b.ts[ct]
            matched = None
            for (plvl, pct) in reversed(recent):
                dtm = (t_now - b.ts[pct]) / 60.0
                if dtm > PAIR_WIN_MIN:
                    break
                if dtm >= MIN_SEP_MIN and abs(lvl - plvl) <= TOL:
                    matched = (plvl, pct)
                    break
            recent.append((lvl, ct))
            if len(recent) > 40:
                recent = recent[-40:]
            if matched is None:
                continue
            if want_high:
                pool = max(lvl, matched[0])          # the high the stops sit above
                if b.mid[ct] < Eb[ct]:               # DOWN bias -> fade the rally short
                    sig_i.append(ct); sig_side.append(-1); sig_level.append(pool)
            else:
                pool = min(lvl, matched[0])          # the low the stops sit below
                if b.mid[ct] > Eb[ct]:               # UP bias -> fade the dip long
                    sig_i.append(ct); sig_side.append(1); sig_level.append(pool)

    scan(sh, h, want_high=True)
    scan(sl, l, want_high=False)

    i = np.asarray(sig_i, np.int64)
    side = np.asarray(sig_side, np.int64)
    level = np.asarray(sig_level, np.float64)
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(n, int),            # LIMIT (maker) resting at the pool level
        level=level,
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, TP_PTS),
        ttl=np.full(n, TTL, np.int64),
    )
