"""strat_m1_turtle_soup -- Liquidity-sweep RECLAIM ("turtle soup") reversal on M1.

FAMILY: liquidity-sweep reclaim / turtle soup (REVERSAL), TF=60 (M1).

MECHANISM
---------
Price pokes BELOW a recent swing low (roll_min of the prior L bars -> sell-side
liquidity / stops resting under the floor), then RECLAIMS back above that level
within one or two bars. That wick-below / close-above is a textbook liquidity
sweep + reclaim: stops got run, price rejected, we fade the sweep in the
direction of the reclaim. Mirror for the short side above a swing high.

  LONG  (bullish turtle soup): l[i] < ref_lo[i]  (bar i took out the L-bar low)
        and c[i] > ref_lo[i]   (closed back above it = reclaim). Stop below the
        sweep wick; enter the reversal up. In an uptrend this is buying a swept
        dip -- the highest-quality version of the setup.
  SHORT (bearish turtle soup): h[i] > ref_hi[i] and c[i] < ref_hi[i].

  A 2-bar variant also fires: sweep on bar i-1 (new L-bar extreme), reclaim close
  on bar i back through the swept level -- catches the reclaim that completes one
  bar late.

Kill-zone gated (London+NY UTC hours) and trend-biased (slow EMA): longs only
when c>EMA, shorts only when c<EMA, so the reclaim runs WITH the higher trend.

WHY THIS ISN'T THE MEAN-REVERT-DIES-AT-COST-FLOOR RESULT
--------------------------------------------------------
Band/vwap fades died because the move-per-trade (~0.26pt at 5s) was smaller than
the round-trip cost. Here we execute on M1 (bar range >> spread), the entry is
gated on a STRUCTURAL sweep of held liquidity (not a raw deviation), and the stop
sits just under the sweep wick so RR is favorable. The reclaim leg is a real
multi-point move that clears the taker cost.

EXIT: fixed RR target by default (TP = RR * stop distance), optionally a chandelier
trail (set TS_TRAIL>0). Time-stop via maxhold.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF.
RUN: .venv/Scripts/python.exe -m bot.micro.runner research/hunt/strat_m1_turtle_soup.py

NO LOOK-AHEAD: ref levels use roll_min/roll_max which EXCLUDE the current bar
(prev-L window, NaN warmup -> np.isfinite gated). Every decision at bar i uses
only c/h/l/o/ATR/EMA up to and including bar i; the engine fills at bar i+1 open
(market) or forward-scans a limit. EMA/ATR are past-only/Wilder-causal.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import hours_mask, ema


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "strat_m1_turtle_soup"
TF = _P("TS_TF", 60, int)                       # M1

# --- exit / sim ---
RR      = _P("TS_RR", 1.8)                       # reward:risk on fixed-target mode
TRAIL   = _P("TS_TRAIL", 0.0)                     # >0 => trail-only (tp=inf)
MAXHOLD = _P("TS_MAXHOLD", 45, int)              # M1 bars (~45 min)
COOLDN  = _P("TS_COOLDOWN", 2, int)
SIM = dict(maxhold=MAXHOLD, dollars_per_point=1.0, commission=0.07,
           cooldown=COOLDN, trail_pts=TRAIL)

# --- structure / trigger ---
LB       = _P("TS_LB", 20, int)                  # swing-pool lookback (M1 bars)
BUF_ATR  = _P("TS_BUF", 0.10)                    # stop buffer beyond sweep wick, in ATR
TWO_BAR  = _P("TS_TWOBAR", 1, int)               # also allow the 1-bar-late reclaim
MIN_PEN  = _P("TS_MINPEN", 0.05)                 # min sweep penetration in ATR (genuine poke)
REJ_FRAC = _P("TS_REJ", 0.30)                    # reclaim close must be >= this frac up the bar range

# --- gates ---
ATR_LO   = _P("TS_ATRLO", 0.30)
ATR_HI   = _P("TS_ATRHI", 30.0)
BIAS_EMA = _P("TS_BIAS", 100, int)               # slow trend bias (M1 bars)
SL_MIN   = _P("TS_SLMIN", 0.8)                   # floor stop distance (pts)
SL_MAX   = _P("TS_SLMAX", 12.0)                  # cap stop distance (pts)
SIDE     = _P("TS_SIDE", 1, int)                 # 0=both, 1=long-only, -1=short-only
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("TS_HOURS", "7,8,9,10,11,12,13,14,15,16").split(","))
KIND     = _P("TS_KIND", 0, int)                 # 0=market (taker, deployable), 1=limit


def generate(b: Bars) -> Signals:
    n = b.n
    c = b.mid
    o = (b.bo + b.ao) * 0.5
    h = (b.bh + b.ah) * 0.5
    l = (b.bl + b.al) * 0.5
    rng = np.maximum(h - l, 1e-9)
    A = atr(b, 14)
    Eb = ema(c, BIAS_EMA)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)
    bias_up = c > Eb
    bias_dn = c < Eb

    ref_lo = roll_min(l, LB)      # prior-L-bar floor (excludes current bar)
    ref_hi = roll_max(h, LB)      # prior-L-bar ceiling
    finite = np.isfinite(ref_lo) & np.isfinite(ref_hi) & np.isfinite(A)

    pen = MIN_PEN * A             # required penetration depth
    # reclaim close strength: fraction of bar range the close sits above the low (long) / below high (short)
    up_close = (c - l) / rng      # ~1 => strong bullish close
    dn_close = (h - c) / rng      # ~1 => strong bearish close

    # ---- LONG: single-bar sweep+reclaim ----
    sweep_lo_1 = finite & sess & volok & bias_up & \
        (l < ref_lo - pen) & (c > ref_lo) & (up_close >= REJ_FRAC)
    # 2-bar: sweep on i-1, reclaim close on i
    sweep_lo_2 = np.zeros(n, bool)
    if TWO_BAR:
        prev_sweep = np.zeros(n, bool)
        prev_sweep[1:] = finite[:-1] & (l[:-1] < ref_lo[:-1] - pen[:-1])
        reclaim = np.zeros(n, bool)
        reclaim[1:] = (c[1:] > ref_lo[:-1]) & (c[1:] > c[:-1])
        sweep_lo_2 = prev_sweep & reclaim & sess & volok & bias_up & finite

    # ---- SHORT: mirror ----
    sweep_hi_1 = finite & sess & volok & bias_dn & \
        (h > ref_hi + pen) & (c < ref_hi) & (dn_close >= REJ_FRAC)
    sweep_hi_2 = np.zeros(n, bool)
    if TWO_BAR:
        prev_sweep_h = np.zeros(n, bool)
        prev_sweep_h[1:] = finite[:-1] & (h[:-1] > ref_hi[:-1] + pen[:-1])
        reclaim_h = np.zeros(n, bool)
        reclaim_h[1:] = (c[1:] < ref_hi[:-1]) & (c[1:] < c[:-1])
        sweep_hi_2 = prev_sweep_h & reclaim_h & sess & volok & bias_dn & finite

    long_ev = sweep_lo_1 | sweep_lo_2
    short_ev = sweep_hi_1 | sweep_hi_2
    if SIDE > 0:
        short_ev[:] = False
    elif SIDE < 0:
        long_ev[:] = False

    sig_i = []; sig_side = []; sig_level = []; sig_sl = []; sig_tp = []

    def emit(i, sd, sweep_wick):
        if sd > 0:
            sl = sweep_wick - BUF_ATR * A[i]
            entry = c[i]
            sl_pts = entry - sl
        else:
            sl = sweep_wick + BUF_ATR * A[i]
            entry = c[i]
            sl_pts = sl - entry
        if not (SL_MIN <= sl_pts <= SL_MAX):
            return
        tp_pts = (np.inf if TRAIL > 0 else RR * sl_pts)
        sig_i.append(int(i)); sig_side.append(int(sd)); sig_level.append(float(entry))
        sig_sl.append(float(sl_pts)); sig_tp.append(float(tp_pts))

    for i in np.where(long_ev)[0]:
        # sweep wick = lowest low across the sweep bar(s) contributing at i
        wick = l[i]
        if i >= 1 and sweep_lo_2[i]:
            wick = min(wick, l[i - 1])
        emit(i, 1, wick)

    for i in np.where(short_ev)[0]:
        wick = h[i]
        if i >= 1 and sweep_hi_2[i]:
            wick = max(wick, h[i - 1])
        emit(i, -1, wick)

    if not sig_i:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array(sig_i, np.int64)
    side = np.array(sig_side, np.int64)
    level = np.array(sig_level, np.float64)
    sl_pts = np.array(sig_sl, np.float64)
    tp_pts = np.array(sig_tp, np.float64)
    ord_ = np.argsort(i, kind="stable")
    i, side, level, sl_pts, tp_pts = i[ord_], side[ord_], level[ord_], sl_pts[ord_], tp_pts[ord_]
    m = len(i)
    kind = np.full(m, KIND, int)
    ttl = np.full(m, 3, np.int64)   # limit stays live only a few bars (unused for market)
    return Signals(i=i, side=side, kind=kind, level=level,
                   sl_pts=sl_pts, tp_pts=tp_pts, ttl=ttl)
