"""Asian-range AMD — London manipulation reversion (maker reclaim-retest). HONEST NEGATIVE.

CONCEPT (accumulation -> manipulation -> distribution):
  * ACCUMULATION: 00:00-06:59 UTC builds the Asian range [AL, AH] (fixed & known after
    07:00 -> fully causal; we only ever act during London).
  * MANIPULATION: early London (07:00-10:59 UTC) sweeps ONE side of the range to take
    resting liquidity (a wick beyond AH or AL by >= SWEEP_MIN, capped at MAX_PEN), then
    closes back inside by >= RECLAIM.
  * DISTRIBUTION: we fade the sweep with a MAKER limit placed back AT the swept level
    (the reclaim-retest): sell-limit at AH on a high-sweep, buy-limit at AL on a low-sweep.
    The limit earns the ~0.66pt spread — the only execution mode that gives this idea any
    survivability at all.

WHY THIS SHAPE (this is the LEAST-BAD cell of an exhaustive search, not a winner):
  Before writing this I measured the post-sweep excursion directly on 2024-01..2025-07:
    - The reclaim FADE has NEGATIVE asymmetry — adverse (continuation) move MEDIAN 3.4pt
      EXCEEDS favorable (reversion) 2.8pt for high-sweeps, and 5.0 vs 3.7 for low-sweeps.
      Price tends to CONTINUE with the sweep, not revert. Fading is structurally -EV.
    - The CONTINUATION breakout (close beyond range -> trade the break) also loses: best
      PF 0.91 (with-bias, tp8/sl4). Entering after the close-beyond is already extended.
    - A full grid over entry window {7-9,7-11,7-13,8-12}, range band {3-12,5-18,8-25,5-32},
      mode {fade/continuation}x{maker/taker}, and tp/sl {4/3..10/5} produced a BEST cell of
      PF 0.92 net -$39 on TRAIN. NOTHING in the concept space is profitable in-sample.
  The single best cell is this maker reversion (window 7-11, range 8-25, tp10/sl5), so it
  is what this module emits — to report a real, honest OOS number for the strongest form.

CONCLUSION (the deliverable): Asian-range AMD has NO live edge on XAU 5s in any tested
form — fade or continuation, taker or maker, across windows/ranges/targets. The residual
maker fade does not clear the acceptance bar (PF<1, net<0 even before the 1.5x stress).
This corroborates the prior asian_amd / asian_amd_maker_revert dead ends from a wider,
better-instrumented search. And it is MAKER-only, so not deployable on the taker MT5 acct.

CONTRACT: generate(b)->Signals (causal) ; SIM ; NAME.
"""
import numpy as np
from bot.micro.engine import Bars, Signals

NAME = "asian_amd_revert_maker_v3"

SIM = dict(maxhold=300, dollars_per_point=1.0, commission=0.07, cooldown=0)

# --- params (best cell of the exhaustive in-sample search) ---
ASIA_A, ASIA_Z = 0, 7
LON_A, LON_Z = 7, 11             # London manipulation killzone window
MIN_RANGE, MAX_RANGE = 8.0, 25.0
SWEEP_MIN = 0.3                  # wick must pierce the level by >= this (a real grab)
MAX_PEN = 6.0                    # but not more (else it is expansion, not a sweep)
RECLAIM = 0.5                    # close back inside the range by >= this
SL_PTS = 5.0
TP_PTS = 10.0
TTL = 120                        # bars the reclaim-retest limit stays live (~10 min)


def generate(b: Bars) -> Signals:
    n = b.n
    mid_h = (b.ah + b.bh) * 0.5
    mid_l = (b.al + b.bl) * 0.5
    sig_i, sig_side, sig_level = [], [], []

    days, starts = np.unique(b.day, return_index=True)
    starts = np.append(starts, n)
    for di in range(len(days)):
        s, e = int(starts[di]), int(starts[di + 1])
        h = b.hod[s:e]
        am = np.where((h >= ASIA_A) & (h < ASIA_Z))[0]
        lon = np.where((h >= LON_A) & (h < LON_Z))[0]
        if len(am) < 200 or len(lon) < 80:
            continue
        am += s
        lon += s
        AH = float(mid_h[am].max())
        AL = float(mid_l[am].min())
        R = AH - AL
        if R < MIN_RANGE or R > MAX_RANGE:
            continue
        du = dd = False
        for j in lon:
            jj = int(j)
            if (not du) and b.ah[jj] > AH + SWEEP_MIN and (b.ah[jj] - AH) <= MAX_PEN \
               and b.bc[jj] < AH - RECLAIM:
                sig_i.append(jj); sig_side.append(-1); sig_level.append(AH); du = True
            if (not dd) and b.bl[jj] < AL - SWEEP_MIN and (AL - b.bl[jj]) <= MAX_PEN \
               and b.bc[jj] > AL + RECLAIM:
                sig_i.append(jj); sig_side.append(1); sig_level.append(AL); dd = True
            if du and dd:
                break

    i = np.asarray(sig_i, np.int64)
    side = np.asarray(sig_side, np.int64)
    level = np.asarray(sig_level, np.float64)
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    m = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(m, int),            # LIMIT (maker) reclaim-retest at the swept level
        level=level,
        sl_pts=np.full(m, SL_PTS),
        tp_pts=np.full(m, TP_PTS),
        ttl=np.full(m, TTL, np.int64),
    )
