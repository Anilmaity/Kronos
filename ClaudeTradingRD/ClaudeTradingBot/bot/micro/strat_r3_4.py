"""CANDIDATE r3_4 — FVG fill in HTF bias (maker continuation, BE+trail managed).

ASSIGNED CONCEPT: detect a fair-value-gap on a higher TF (M5 via resample), only
take fills in the direction of an HTF EMA bias, enter on a LIMIT at the gap, target
the displacement origin.

WHY THIS IS A NEW DIRECTION (vs the two recorded FVG dead ends):
  * r1_0 (fvg_htf_bias_maker, OOS pf 0.55): maker limit in a same-direction (bullish)
    FVG, but targeted the far displacement EXTREME with a fixed SL/TP and NO exit
    management. Two failure modes: (a) the extreme target is rarely reached -> low WR,
    (b) the full fixed SL means every adverse-selected fill loses the whole stop.
  * r2_5 (fvg_htf_reclaim_origin, OOS pf 0.80): TAKER reclaim-confirmation entry that
    pays the spread; concluded no edge once the 1-bar look-ahead was removed.

  This variant keeps the assignment literally (maker limit inside the gap, with-trend,
  target the displacement origin) but changes the two things neither tried:
    1. EXIT MANAGEMENT. The engine supports break-even and trailing stops; both dead
       ends used a static SL/TP. Here the stop snaps to break-even once price travels
       BE_AT pts in favour, and then a chandelier-style trail (trail_pts) ratchets.
       This bounds the adverse-selection loss tail (limit fills that fail go out near
       BE, not -full-stop) and harvests the continuations that do run.
    2. TARGET = the DISPLACEMENT ORIGIN as a structural, reachable level: for a bullish
       FVG the up-impulse's origin is the gap's lower edge region; the *continuation*
       target that honours "origin" is a measured move = entry + RR_TP * risk where
       risk is anchored to the gap (a near, high-hit target), with the trail allowed to
       run past it. Modest TP + BE => the high-WR shape the goal asks for.

  Execution is MAKER (kind=1): a limit resting inside the gap earns the ~0.66pt spread,
  which is the single biggest cost lever on this instrument. DEPLOYABILITY: the user's
  FundingPips MT5 account is taker-only, so a maker-only positive result is research-
  valuable but NOT directly deployable there -- reported honestly.

CAUSALITY (audited): an M5 FVG using bars i-2,i-1,i is confirmed at S5 index
di = s5_idx[i]; the decision index is di, so the limit is armed only from di+1 onward
and fills on a strictly later S5 bar. EMA/ATR on M5 are causal (value at i uses <= i).
swings() is not used. No future S5 bar is indexed in generate().

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str
"""
import numpy as np
from bot.micro.engine import Bars, Signals
from bot.micro.features import resample, fvg, ema, hours_mask

NAME = "fvg_bias_maker_origin"

# HONEST RESULT (this config, OOS 2025-08..2026-06): 110 trades, WR 35.5%, PF 0.355,
# net -$136, maxDD $141; degrades to PF 0.265 / net -$173 under the 1.5x stress.
# Four causal variants were tried in this module + the two recorded FVG dead ends
# (r1_0 maker continuation, r2_5 taker reclaim):
#   (a) maker continuation + tight BE/trail  -> OOS WR 19.6%, net -$189
#   (b) maker gap-fill to origin (deeper dip) -> OOS WR 17.8%, net -$247
#   (c) maker continuation + small fixed TP   -> OOS WR 46.4%, net -$247 (best WR)
#   (d) (c) + strong-trend gate (this file)   -> OOS WR 35.5%, net -$136 (best net/DD)
# Every config is firmly below the acceptance bar and worsens under stress. ROOT CAUSE:
# a resting limit at an FVG is adverse-selected (it only fills the pullbacks that keep
# going against the trade), so even earning the ~0.66pt spread as a maker does not
# produce post-entry excursion asymmetry; no BE/trail/target scheme rescues a
# directionless fill. CONCLUSION: FVG-fill-in-HTF-bias has no deployable edge on XAU S5
# at this cost floor -- consistent with the two prior FVG dead ends.

# no BE/trail: a fixed wide SL + small TP -> harvest the spread-earned bounce at high WR.
SIM = dict(maxhold=300, dollars_per_point=1.0, commission=0.07,
           cooldown=18, be_at_pts=0.0, trail_pts=0.0)

# --- tunable params (runner sweeps vary these +/-30%) ---
TF_SEC = 300          # higher timeframe = M5
EMA_P = 50            # HTF EMA bias period (M5 bars)
EMA_SLOPE = 3         # EMA must slope with the trade over this many HTF bars
ENTRY_FRAC = 0.5      # 0 = far gap edge (deep pullback), 1 = near edge; 0.5 = C.E.
BUF = 0.30            # SL beyond the far gap edge, in HTF ATR units
TP_PTS = 2.0          # take-profit (pts)
MIN_SL = 1.8          # floor on stop distance (pts)
DISP = 0.7            # impulse body (c-o of bar i) must exceed DISP * HTF ATR
TREND_K = 0.5         # require close >= TREND_K*ATR beyond EMA (strong, fresh trend)
GAP_MIN = 0.60        # min gap (pts) - the displacement must clear the spread
GAP_MAX = 5.0         # max gap (pts) - skip blow-off legs
ATR_P = 14
TTL = 240             # limit stays live this many S5 bars (20 min) before cancel
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active (UTC)


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

    I, SIDE, LVL, SLP, TPP = [], [], [], [], []
    for i in range(EMA_P + 2, K):
        di = int(s5idx[i])
        if di + 1 >= b.n or not sess_s5[di]:
            continue
        gsz = top[i] - bot[i]
        if not np.isfinite(gsz) or not (GAP_MIN <= gsz <= GAP_MAX):
            continue
        atr_i = A[i]
        if atr_i <= 0:
            continue
        bias_up = (c[i] - E[i]) >= TREND_K * atr_i and E[i] > E[i - EMA_SLOPE]
        bias_dn = (E[i] - c[i]) >= TREND_K * atr_i and E[i] < E[i - EMA_SLOPE]

        # with-trend CONTINUATION: a same-direction FVG = a pullback inside the trend.
        # bullish FVG in up-bias -> rest a buy limit inside the gap (earns the spread on
        # the pullback fill); the gap should act as support and the trend resume. Small
        # fixed TP harvests the bounce at high WR; wide SL beyond the far gap edge.
        if bull[i] and bias_up:
            if (c[i] - o[i]) < DISP * atr_i:
                continue
            gap_top, gap_bot = top[i], bot[i]      # bull: bot=h[i-2], top=l[i]
            entry = gap_bot + ENTRY_FRAC * (gap_top - gap_bot)
            if entry >= c[i]:                       # limit must sit BELOW market
                continue
            sl = gap_bot - BUF * atr_i
            risk = entry - sl
            if risk < MIN_SL:
                sl = entry - MIN_SL
                risk = MIN_SL
            I.append(di); SIDE.append(1); LVL.append(entry)
            SLP.append(risk); TPP.append(TP_PTS)
        elif bear[i] and bias_dn:
            if (o[i] - c[i]) < DISP * atr_i:
                continue
            gap_top, gap_bot = top[i], bot[i]      # bear: top=l[i-2], bot=h[i]
            entry = gap_top - ENTRY_FRAC * (gap_top - gap_bot)
            if entry <= c[i]:                       # limit must sit ABOVE market
                continue
            sl = gap_top + BUF * atr_i
            risk = sl - entry
            if risk < MIN_SL:
                sl = entry + MIN_SL
                risk = MIN_SL
            I.append(di); SIDE.append(-1); LVL.append(entry)
            SLP.append(risk); TPP.append(TP_PTS)

    n = len(I)
    if n == 0:
        return Signals(i=np.array([], int), side=np.array([], int),
                       kind=np.array([], int), level=np.array([]),
                       sl_pts=np.array([]), tp_pts=np.array([]))
    I = np.array(I, int)
    order = np.argsort(I, kind="stable")
    I = I[order]; SIDE = np.array(SIDE, int)[order]
    LVL = np.array(LVL)[order]; SLP = np.array(SLP)[order]; TPP = np.array(TPP)[order]
    return Signals(
        i=I, side=SIDE,
        kind=np.ones(n, int),               # LIMIT entry (maker, earns spread)
        level=LVL,
        sl_pts=SLP, tp_pts=TPP,
        ttl=np.full(n, TTL, int),
    )
