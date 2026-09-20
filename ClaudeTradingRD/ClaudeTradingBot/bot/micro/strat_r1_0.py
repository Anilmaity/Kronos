"""CANDIDATE r1_0 — FVG fill in HTF bias (continuation pullback, MAKER entry).

CONCEPT (assigned):
  Detect a fair-value-gap on a higher TF (M5 via features.resample). Only take a
  gap-fill in the direction of an HTF EMA bias. Enter on a LIMIT inside the gap
  (consequent-encroachment), target the displacement extreme (the high/low the
  impulse reached), stop just beyond the far edge of the gap.

  Interpretation note: the assignment says "target the displacement origin"; for a
  trend-CONTINUATION long (HTF bias up, bullish FVG = up-displacement, buy the
  pullback into the gap) the only profitable target is the reach of the impulse
  leg, so TP = the impulse extreme (max high of the displacement window). SL sits
  beyond the gap's far edge = the classic FVG invalidation. Entry is a limit at
  the gap mid -> earns the spread (kind=1). Causal: an M5 FVG confirmed at bar i is
  only actioned from S5 index s5_idx[i]+1; all features use bars <= i.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str
"""
import numpy as np
from bot.micro.engine import Bars, Signals
from bot.micro.features import resample, fvg, ema, hours_mask

NAME = "fvg_htf_bias_maker"

SIM = dict(maxhold=240, dollars_per_point=1.0, commission=0.07, cooldown=24)

# --- tunable params (runner sweeps vary these +/-30%) ---
TF_SEC = 300        # higher timeframe = M5
EMA_P = 50          # HTF EMA bias period (M5 bars ~ 4.2h)
EMA_SLOPE = 3       # bias must be rising/falling over this many HTF bars
ENTRY_FRAC = 0.5    # 0=deep edge, 1=near edge; 0.5 = consequent encroachment
BUF = 0.5           # SL beyond far gap edge, in units of HTF ATR
MIN_RR = 1.2        # require reward/risk >= this to take the setup
DISP = 0.8          # displacement body must exceed DISP * HTF ATR (real impulse)
GAP_MIN = 0.30      # min gap size (pts) - must clear the spread
GAP_MAX = 4.0       # max gap size (pts) - skip blow-off gaps
ATR_P = 14
TTL = 360           # limit stays live this many S5 bars (30 min) before cancel
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15, 16)  # London + NY


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

    # S5 hour-of-day at the decision bar (causal session filter)
    sess_s5 = hours_mask(b, SESSION_HOURS)

    I, SIDE, LVL, SLP, TPP = [], [], [], [], []
    for i in range(EMA_P + 2, K):
        di = int(s5idx[i])
        if di + 1 >= b.n or not sess_s5[di]:
            continue
        gsz = top[i] - bot[i]
        if not (GAP_MIN <= gsz <= GAP_MAX):
            continue
        disp_up = (c[i - 1] - o[i - 1]) >= DISP * A[i - 1]
        disp_dn = (o[i - 1] - c[i - 1]) >= DISP * A[i - 1]
        bias_up = c[i] > E[i] and E[i] > E[i - EMA_SLOPE]
        bias_dn = c[i] < E[i] and E[i] < E[i - EMA_SLOPE]
        if bull[i] and bias_up and disp_up:
            gap_top, gap_bot = top[i], bot[i]
            entry = gap_bot + ENTRY_FRAC * (gap_top - gap_bot)
            sl = gap_bot - BUF * A[i]
            tgt = max(h[i - 1], h[i])           # displacement extreme
            risk = entry - sl
            rew = tgt - entry
            if risk > 0 and rew > 0 and rew / risk >= MIN_RR and entry < c[i]:
                I.append(di); SIDE.append(1); LVL.append(entry)
                SLP.append(risk); TPP.append(rew)
        elif bear[i] and bias_dn and disp_dn:
            gap_top, gap_bot = top[i], bot[i]
            entry = gap_top - ENTRY_FRAC * (gap_top - gap_bot)
            sl = gap_top + BUF * A[i]
            tgt = min(l[i - 1], l[i])
            risk = sl - entry
            rew = entry - tgt
            if risk > 0 and rew > 0 and rew / risk >= MIN_RR and entry > c[i]:
                I.append(di); SIDE.append(-1); LVL.append(entry)
                SLP.append(risk); TPP.append(rew)

    n = len(I)
    if n == 0:
        return Signals(i=np.array([], int), side=np.array([], int),
                       kind=np.array([], int), level=np.array([]),
                       sl_pts=np.array([]), tp_pts=np.array([]))
    order = np.argsort(np.array(I), kind="stable")
    I = np.array(I)[order]; SIDE = np.array(SIDE)[order]
    LVL = np.array(LVL)[order]; SLP = np.array(SLP)[order]; TPP = np.array(TPP)[order]
    return Signals(
        i=I, side=SIDE,
        kind=np.ones(n, int),               # LIMIT entry (earns spread)
        level=LVL,
        sl_pts=SLP, tp_pts=TPP,
        ttl=np.full(n, TTL, int),
    )
