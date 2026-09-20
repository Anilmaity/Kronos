"""Asian-range AMD — London manipulation reversal (maker reclaim-retest), bias-aligned.

Concept (accumulation -> manipulation -> distribution):
  * ACCUMULATION: the Asian session (00:00-06:59 UTC) builds a range [al, ah].
  * MANIPULATION: early London (07:00-11:59 UTC) sweeps ONE side of that range to
    take resting liquidity, pokes at most MAX_PEN beyond it, then closes back inside
    by >= RECLAIM (a fakeout / reclaim).
  * DISTRIBUTION: price reverts into the range / expands in the *true* daily direction.

Two scout findings shaped this:
  (1) A bare "fade any sweep" has NO edge — post-sweep excursion is ~symmetric. The
      asymmetry only appears when the manipulation runs AGAINST the higher-timeframe
      bias and we trade WITH that bias. Bias is sampled ONCE per day at the
      London-open bar from a slow causal EMA so it can never contradict the (local)
      sweep extreme:  bias UP -> only LOW sweeps -> LONG ;  bias DOWN -> HIGH sweeps -> SHORT.
  (2) Maker (limit) entry earns the ~0.66pt spread and is the only execution mode
      that gives this idea any survivability. Entry is therefore a LIMIT placed back
      AT the swept Asian level (the reclaim-retest): for a long we buy a dip back to
      al; for a short we sell a pop back to ah. Only the FIRST qualifying sweep/day.

HONEST RESULT (this is a research deliverable, not a pass): even in its best honest
form this concept does NOT clear the acceptance bar. Across reversion fades, momentum-
confirmed reversions, and break/retest continuations, taker execution is net-negative
on OOS (PF ~0.6-0.75). This maker variant is the least-bad — OOS PF ~0.8, net still
slightly negative — and it is MAKER-ONLY, so it is not deployable on the taker-only
FundingPips MT5 account. Conclusion with evidence: Asian-range AMD has no live taker
edge on XAU 5s; the residual is a thin maker reclaim that the spread alone barely
fails to cover.

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only.
"""
import numpy as np
from bot.micro.engine import Bars, Signals
from bot.micro.features import ema

NAME = "asian_amd_maker_revert"

SIM = dict(maxhold=300, dollars_per_point=1.0, commission=0.07, cooldown=0)

# --- tunable params (runner sweeps ±30%) ---
EMA_BIAS = 5760      # slow EMA for daily bias (~8h of 5s bars)
RNG_LO   = 7.0       # min Asian range (pts) — skip dead days
RNG_HI   = 55.0      # max Asian range (pts) — skip runaway days
MAX_PEN  = 4.0       # sweep may poke at most this far beyond the level
RECLAIM  = 0.4       # close must reclaim this many pts back inside the range
SL_PTS   = 5.0       # stop distance from the fill (sits beyond the manipulation wick)
TP_PTS   = 7.0       # target distance (reversion into the range)
TTL      = 120       # bars the reclaim-retest limit stays live (~10 min)
ASIA_A, ASIA_Z = 0, 7
LON_A,  LON_Z  = 7, 12


def generate(b: Bars) -> Signals:
    hod = b.hod
    mid = b.mid
    Eb = ema(mid, EMA_BIAS)

    sig_i, sig_side, sig_level = [], [], []
    for dd in np.unique(b.day):
        idx = np.where(b.day == dd)[0]
        if len(idx) < 400:
            continue
        h = hod[idx]
        asia = idx[(h >= ASIA_A) & (h < ASIA_Z)]
        lon = idx[(h >= LON_A) & (h < LON_Z)]
        if len(asia) < 200 or len(lon) < 100:
            continue
        ah = float(b.ah[asia].max())
        al = float(b.bl[asia].min())
        rng = ah - al
        if rng < RNG_LO or rng > RNG_HI:
            continue
        lon_open = int(lon[0])
        bias_up = mid[lon_open] > Eb[lon_open]
        if bias_up:
            for j in lon:
                jj = int(j)
                if b.bl[jj] < al and (al - b.bl[jj]) <= MAX_PEN and b.bc[jj] > al + RECLAIM:
                    sig_i.append(jj); sig_side.append(1); sig_level.append(al)
                    break
        else:
            for j in lon:
                jj = int(j)
                if b.ah[jj] > ah and (b.ah[jj] - ah) <= MAX_PEN and b.bc[jj] < ah - RECLAIM:
                    sig_i.append(jj); sig_side.append(-1); sig_level.append(ah)
                    break

    i = np.asarray(sig_i, np.int64)
    side = np.asarray(sig_side, np.int64)
    level = np.asarray(sig_level, np.float64)
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(n, int),            # LIMIT (maker) reclaim-retest at the swept level
        level=level,
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, TP_PTS),
        ttl=np.full(n, TTL, np.int64),
    )
