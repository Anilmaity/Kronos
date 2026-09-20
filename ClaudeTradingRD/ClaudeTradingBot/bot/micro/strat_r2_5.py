"""CANDIDATE r2_5 — FVG fill in HTF bias (with-trend RECLAIM entry, target = origin).

ASSIGNED CONCEPT: detect a fair-value-gap on a higher TF (M5 via resample), only
take fills in the direction of an HTF EMA bias, enter at the gap, target the
displacement ORIGIN.

HOW THIS DIFFERS FROM THE DEAD END (r1_0 = fvg_htf_bias_maker, OOS pf 0.55):
  r1_0 used a passive LIMIT in a SAME-direction (continuation) gap and targeted the
  far displacement EXTREME. It suffered adverse selection (the limit only fills the
  impulses that fail) and a target that is rarely reached.

  This variant trades the OPPOSING (pullback) gap WITH the trend, and crucially
  waits for a RECLAIM confirmation instead of entering blind:
    * HTF bias UP  -> a BEARISH M5 FVG is a sharp 3-bar DOWN-leg = a pullback. Arm
      it. Only ENTER LONG (market) once an S5 bar CLOSES back above the gap's upper
      edge (l[i-2]) = the dip is being bought / reclaimed. Stop below the pullback
      low; target = the displacement ORIGIN (h[i-2]) via an R-multiple.
    * HTF bias DOWN -> mirror with a BULLISH M5 FVG (up-leg pullback).
  The reclaim filter is meant to avoid the knife-catch of entering at the pullback
  low (which scored WR ~30%) by demanding evidence the move resumes with the trend.

CAUSALITY (audited): the M5 FVG at bar i uses bars i-2,i-1,i and is confirmed at
S5 index di=s5_idx[i]. The reclaim is detected on a STRICTLY LATER S5 bar ei
(di < ei), and the trade decision index is ei itself, so the engine enters at the
NEXT S5 bar (ei+1) market open — the confirming close is fully formed before entry.
EMA/ATR on M5 are causal. No future bar is indexed. (An earlier draft that set the
decision index to ei-1 was a 1-bar look-ahead and inflated PF from ~0.6 to ~1.5;
fixing it removed the entire apparent edge — recorded here as honest evidence.)

EXECUTION: MARKET (kind=0, taker) — deployable on the user's FundingPips MT5
account. The edge must clear the real spread, not earn it.

HONEST RESULT: this concept does NOT pass the acceptance bar. Across the full
design space (taker dip-reversal, taker momentum continuation, maker limit
continuation, and this reclaim variant) every causal config at a tradeable
frequency lands at OOS PF ~0.5-0.9 with negative net, and degrades further under
the 1.5x cost stress. The only positive configs were either a look-ahead artifact
or degenerate (<0.2 trades/day, <30 OOS trades). The FVG-fill-in-HTF-bias trigger
has no deployable directional edge on XAU S5 at the real cost floor.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str
"""
import numpy as np
from bot.micro.engine import Bars, Signals
from bot.micro.features import resample, fvg, ema, hours_mask

NAME = "fvg_htf_reclaim_origin"

SIM = dict(maxhold=360, dollars_per_point=1.0, commission=0.07, cooldown=12)

# --- tunable params (runner sweeps vary these +/-30%) ---
TF_SEC = 300          # higher timeframe = M5
EMA_P = 60            # HTF EMA bias period (M5 bars)
EMA_SLOPE = 3         # EMA must slope with the trade over this many HTF bars
BUF = 0.40            # SL beyond the pullback extreme, in units of HTF ATR
RR = 2.5              # target = RR * risk (anchored toward the displacement origin)
MIN_SL = 1.2          # floor on stop distance (pts) so a sub-spread stop is never used
GAP_MIN = 0.70        # min gap size (pts) - the pullback leg must be a real displacement
GAP_MAX = 4.0         # max gap size (pts) - skip blow-off legs
ATR_P = 14
CONF_W = 90           # scan up to this many S5 bars (7.5 min) for the reclaim
SESSION_HOURS = (7, 8, 9, 12, 13, 14)   # London open + NY open (active hours, UTC)


def _htf_atr(h, l, c, p):
    n = len(h)
    tr = np.empty(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    out = np.empty(n)
    out[0] = tr[0]
    a = 1.0 / p
    for i in range(1, n):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
    return out


def generate(b: Bars) -> Signals:
    R = resample(b, TF_SEC)
    o, h, l, c = R["o"], R["h"], R["l"], R["c"]
    s5idx = R["s5_idx"]
    K = len(c)
    E = ema(c, EMA_P)
    A = _htf_atr(h, l, c, ATR_P)
    bull, bear, top, bot = fvg(o, h, l, c)
    sess_s5 = hours_mask(b, np.array(SESSION_HOURS))

    bc, ac = b.bc, b.ac
    I, SIDE, SLP, TPP = [], [], [], []
    for i in range(EMA_P + 2, K):
        di = int(s5idx[i])
        if di + 1 >= b.n or not sess_s5[di]:
            continue
        gsz = top[i] - bot[i]
        if not np.isfinite(gsz) or not (GAP_MIN <= gsz <= GAP_MAX):
            continue
        bias_up = c[i] > E[i] and E[i] > E[i - EMA_SLOPE]
        bias_dn = c[i] < E[i] and E[i] < E[i - EMA_SLOPE]

        if bear[i] and bias_up:
            side = 1
            pull_lo = l[i]                       # pullback low
            reclaim_lvl = top[i]                 # upper gap edge = l[i-2]
            sl_dist = (c[i] - (pull_lo - BUF * A[i]))
        elif bull[i] and bias_dn:
            side = -1
            pull_hi = h[i]                        # pullback high
            reclaim_lvl = bot[i]                 # lower gap edge = l[i] (bull bot=h[i-2]) -> use bot
            sl_dist = ((pull_hi + BUF * A[i]) - c[i])
        else:
            continue

        if sl_dist < MIN_SL:
            sl_dist = MIN_SL
        if sl_dist <= 0:
            continue

        # ---- causal reclaim scan on STRICTLY LATER S5 bars ----
        ei = -1
        jmax = min(di + 1 + CONF_W, b.n)
        j = di + 1
        while j < jmax:
            if b.ts[j] - b.ts[j - 1] > 30:       # don't scan across a gap
                break
            if side > 0 and bc[j] > reclaim_lvl:
                ei = j; break
            if side < 0 and ac[j] < reclaim_lvl:
                ei = j; break
            j += 1
        if ei < 0:
            continue

        # decision at the confirming bar's close -> engine enters next bar (ei+1)
        I.append(ei); SIDE.append(side)
        SLP.append(sl_dist); TPP.append(RR * sl_dist)

    n = len(I)
    if n == 0:
        return Signals(i=np.array([], int), side=np.array([], int),
                       kind=np.array([], int), level=np.array([]),
                       sl_pts=np.array([]), tp_pts=np.array([]))
    I = np.array(I, int)
    order = np.argsort(I, kind="stable")
    I = I[order]; SIDE = np.array(SIDE, int)[order]
    SLP = np.array(SLP)[order]; TPP = np.array(TPP)[order]
    return Signals(
        i=I, side=SIDE,
        kind=np.zeros(n, int),              # MARKET entry next bar (taker, deployable)
        level=np.zeros(n),
        sl_pts=SLP, tp_pts=TPP,
    )
