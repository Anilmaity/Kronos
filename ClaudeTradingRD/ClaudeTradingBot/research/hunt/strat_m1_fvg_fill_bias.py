"""FVG-FILL (retrace into an unfilled FVG toward its origin) -- M1, HTF-bias gated.

FAMILY (assigned): Fair Value Gap fill. Detect a 3-bar M1 FVG (gap between
bar[i-2] extreme and bar[i] extreme). On a LATER retrace back INTO the gap, enter
toward the gap's origin (the retrace is the "fill"); ride the with-trend leg.
HTF-bias gated by a slow EMA on the M1 series. Kill-zone gated to London 07-10 and
NY 12-15 UTC.

READING (HTF-aligned, gold is a 2024-26 uptrend so LONG is the default edge):
  In an UP EMA bias, a WITH-trend BULLISH FVG (l[i] > h[i-2]) forms below price after
  an up displacement. Zone = [bot=h[i-2] (origin of the leg), top=l[i]]. Price tends to
  RETRACE DOWN into that unfilled gap before the trend resumes -- the classic ICT "fill
  the FVG" pullback entry. We rest a LIMIT LONG inside the gap (the retrace toward
  origin bot IS the fill), stop just below the gap origin, and a chandelier TRAIL so the
  resumed leg runs while the loss tail is bounded. Mirror for a DOWN bias + bearish FVG.

  This differs from the with-trend BOS *continuation* template (strat_m1_r2_0, which
  needs a structure break and is short-only): here the trigger is the RETRACE-INTO-GAP
  fill itself, the bias EMA is on the M1 working series (not an M5 resample), and the
  default is LONG (the dead-end log shows shorts lose against gold's uptrend).

FREQUENCY via MORE KILL-ZONE WINDOWS (London + NY) and a union over the immediate FVG
  plus its bias context -- NOT by loosening the trigger into noise. The gap-size FLOOR
  (GAP_MIN) keeps only displacements whose retrace->resume move can clear a real broker
  spread; dropping it collapses PF through the cost floor (see research dead_ends).

CAUSALITY (audited, no look-ahead): TF=60 -> runner feeds M1 bars. The FVG at bar i
  uses bars i-2,i-1,i, confirmed at CLOSE of i; the LIMIT is placed for bars STRICTLY
  AFTER i (engine scans di+1..di+ttl and fills only on a real touch). The EMA bias and
  ATR are past-only/Wilder-causal; roll_max/min exclude the current bar and are
  np.isfinite-gated. No future bar is ever indexed; `level` is built only from bar<=i
  values (the gap edges of bar i). Absolute imports; single position at a time.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str ; TF=60
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import fvg, ema, hours_mask


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "m1_fvg_fill_origin_bias"
TF = 60   # M1 execution timeframe (seconds)

# --- exit / sim ---
MAXHOLD = _P("FVG_MAXHOLD", 60, int)     # M1 bars time-stop (~1h)
TRAIL   = _P("FVG_TRAIL", 1.2)           # chandelier trail (pts); tp=inf trail-only when >0
COOLDOWN = _P("FVG_COOLDOWN", 2, int)
SIM = dict(maxhold=MAXHOLD, dollars_per_point=1.0, commission=0.07,
           cooldown=COOLDOWN, trail_pts=TRAIL)

# --- HTF bias (EMA on the M1 series) ---
EMA_P     = _P("FVG_EMAP", 100, int)
EMA_SLOPE = _P("FVG_SLOPE", 5, int)      # EMA must slope with the trade over this many M1 bars

# --- FVG fill gate ---
GAP_MIN = _P("FVG_GMIN", 1.5)            # min gap (pts): the spread-clearance floor
GAP_MAX = _P("FVG_GMAX", 8.0)            # max gap (pts): skip blow-off legs
ATR_P   = _P("FVG_ATRP", 14, int)
BUF_ATR = _P("FVG_BUF", 0.5)            # stop beyond the gap origin, in M1 ATR units
PEN     = _P("FVG_PEN", 0.5)            # limit penetration into the gap (0.5 = mid-gap)
TTL     = _P("FVG_TTL", 20, int)        # M1 bars the limit stays live
SL_MIN  = _P("FVG_SLMIN", 1.0)
SL_MAX  = _P("FVG_SLMAX", 16.0)
KDISP   = _P("FVG_KDISP", 0.0)          # 3-bar displacement floor: |c[i]-c[i-2]| >= K*ATR
SIDE    = _P("FVG_SIDE", 1, int)        # 1=long-only, -1=short-only, 0=both
# kill zones: London 07-10, NY 12-15 UTC
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("FVG_HOURS", "7,8,9,12,13,14").split(","))


def _empty():
    z = np.zeros(0)
    return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)


def generate(b: Bars) -> Signals:
    n = b.n
    o = (b.ao + b.bo) * 0.5
    h = (b.ah + b.bh) * 0.5
    l = (b.al + b.bl) * 0.5
    c = b.mid

    if n <= EMA_P + EMA_SLOPE + 3:
        return _empty()

    A = atr(b, ATR_P)
    E = ema(c, EMA_P)
    # slope-confirmed EMA bias on the M1 series (past-only)
    bias_up = np.zeros(n, bool)
    bias_dn = np.zeros(n, bool)
    bias_up[EMA_SLOPE:] = (c[EMA_SLOPE:] > E[EMA_SLOPE:]) & (E[EMA_SLOPE:] > E[:-EMA_SLOPE])
    bias_dn[EMA_SLOPE:] = (c[EMA_SLOPE:] < E[EMA_SLOPE:]) & (E[EMA_SLOPE:] < E[:-EMA_SLOPE])

    bull, bear, top, bot = fvg(o, h, l, c)
    sess = hours_mask(b, np.array(SESSION_HOURS))

    I, SIDE_, LVL, SLP, TPP = [], [], [], [], []
    for i in range(2, n):
        if not sess[i] or i + 1 >= n:
            continue
        gsz = top[i] - bot[i]
        if not np.isfinite(gsz) or not (GAP_MIN <= gsz <= GAP_MAX):
            continue
        a = A[i]
        if not np.isfinite(a) or a <= 0:
            continue
        if KDISP > 0 and abs(c[i] - c[i - 2]) < KDISP * a:
            continue

        if bull[i] and bias_up[i] and SIDE >= 0:
            # UP bias, with-trend bullish FVG below price -> retrace DOWN into gap
            # (fill toward origin bot) -> LIMIT LONG inside the gap, ride resumed leg
            side = 1
            level = top[i] - PEN * gsz
            stop = bot[i] - BUF_ATR * a
            sl_pts = level - stop
            if level >= c[i]:            # must be a genuine retrace below current price
                continue
        elif bear[i] and bias_dn[i] and SIDE <= 0:
            # DOWN bias, with-trend bearish FVG above price -> retrace UP into gap
            side = -1
            level = bot[i] + PEN * gsz
            stop = top[i] + BUF_ATR * a
            sl_pts = stop - level
            if level <= c[i]:
                continue
        else:
            continue

        if not (SL_MIN <= sl_pts <= SL_MAX):
            continue

        I.append(i); SIDE_.append(side); LVL.append(level)
        SLP.append(sl_pts); TPP.append(np.inf)   # trail-only exit

    if not I:
        return _empty()
    I = np.array(I, np.int64)
    order = np.argsort(I, kind="stable")
    return Signals(
        i=I[order],
        side=np.array(SIDE_, np.int64)[order],
        kind=np.ones(len(I), np.int64),      # LIMIT entry (re-priced as taker on the grid)
        level=np.array(LVL, np.float64)[order],
        sl_pts=np.array(SLP, np.float64)[order],
        tp_pts=np.array(TPP, np.float64)[order],
        ttl=np.full(len(I), TTL, np.int64),
    )
