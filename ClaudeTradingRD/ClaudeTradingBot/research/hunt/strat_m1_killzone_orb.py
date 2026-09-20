"""Kill-zone opening-range breakout (bias-gated) on M1 -- freq via MORE sessions.

FAMILY / IDEA
-------------
Mirror the proven M5 session-breakout (EMA-bias, first-N-min opening range, stop-
entry on the break) but run it on M1 (TF=60) across SEVERAL kill-zone sub-windows
to lift frequency without loosening the trigger. For each kill-zone HOUR (London
07,08 UTC and NY 12,13,14,15 UTC by default), the opening range (OR) is the first
ORN minutes of that hour. After the OR completes, during the rest of that hour, the
FIRST close that breaks the OR high (with EMA240 bias up) fires a LONG; the first
close below the OR low (bias down) fires a SHORT. Entry is a MARKET order on the
next bar open -- a genuine stop-entry breakout, and market-execution is exactly how
the taker-only FundingPips account fills. Stop sits on the far side of the OR
(structure stop), and a chandelier trail lets the continuation leg run.

WHY MORE SESSIONS, NOT LOOSER TRIGGERS
--------------------------------------
Frequency comes from having up to 6 independent kill-zone ranges per day (each can
print at most ONE breakout). The trigger itself (close beyond a completed OR, gated
by the slow EMA bias and an OR-width/ATR sanity filter) is NOT loosened -- the repo
has proven that looser triggers (shorter TTL, lower displacement floor) collapse PF
through 1.0. Here the only frequency lever is the count of kill-zones.

COST-ACCOUNTING NOTE (read before judging the taker grid)
---------------------------------------------------------
This family uses MARKET (kind=0) entries, so a round trip already crosses the full
spread once inside the runner's *maker* column (buy the ask, sell the bid). For a
market strategy the grid's MAKER column IS the realistic single-spread taker cost;
the grid's TAKER column adds a SECOND full spread (~2x round-trip cost) and therefore
over-penalizes a market breakout relative to a resting-limit strategy. Both are
reported honestly; the fair live-cost read for this module is maker@0.25 with the
grid-taker@0.25 as a hard stress bound.

NO LOOK-AHEAD
-------------
Every OR high/low is built only from bars whose minute-of-hour < ORN, all of which
occur strictly BEFORE the trade-window bars that use them (same day+hour group). The
break is judged on close[i]; the engine fills on i+1 open. ATR (Wilder) and EMA are
past-only. roll_max/min not needed. No future bar is ever indexed. Absolute imports.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF=60.
RUN: .venv/Scripts/python.exe -m bot.micro.runner research/hunt/strat_m1_killzone_orb.py
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import ema


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "m1_killzone_orb"
TF = 60  # M1

# kill-zone hours (UTC): London 07,08 ; NY 12,13,14,15
KZ_HOURS = tuple(int(x) for x in os.environ.get("KZ_HOURS", "7,8,12,13,14,15").split(","))
ORN      = _P("KZ_ORN", 15, int)      # opening-range length in minutes (first ORN of the hour)
TRADE_END = _P("KZ_TEND", 60, int)    # trade window ends at this minute-of-hour (<=60)
BIAS_EMA = _P("KZ_BIAS", 240, int)    # slow EMA trend bias on M1 (240m = 4h)
BUF_ATR  = _P("KZ_BUF", 0.25)         # stop buffer beyond OR far edge, in ATR
KSL      = _P("KZ_KSL", 0.0)          # if >0, stop = KSL*ATR (overrides structure stop)
RR       = _P("KZ_RR", 0.0)           # if >0, fixed target = RR*stop (else trail-only)
TRAIL    = _P("KZ_TRAIL", 5.0)        # chandelier trail distance (pts); used when RR<=0
MAXHOLD  = _P("KZ_MAXHOLD", 60, int)  # time-stop in M1 bars (~1h)
SL_MIN   = _P("KZ_SLMIN", 1.5)        # floor on stop distance (pts)
SL_MAX   = _P("KZ_SLMAX", 14.0)       # cap on stop distance (pts) -> reject fat ranges
OR_WMIN  = _P("KZ_ORWMIN", 0.5)       # OR width must be >= this * ATR (skip dead ranges)
OR_WMAX  = _P("KZ_ORWMAX", 6.0)       # OR width must be <= this * ATR (skip blow-out ranges)
K_BRK    = _P("KZ_KBRK", 1.00)        # DISPLACEMENT floor: close must clear OR edge by >=K*ATR
ATR_LO   = _P("KZ_ATRLO", 0.30)
ATR_HI   = _P("KZ_ATRHI", 40.0)
SIDE     = _P("KZ_SIDE", 1, int)      # 0=both, 1=long-only, -1=short-only

SIM = dict(maxhold=MAXHOLD, dollars_per_point=1.0, commission=0.07,
           cooldown=_P("KZ_COOLDOWN", 0, int), trail_pts=(0.0 if RR > 0 else TRAIL))


def generate(b: Bars) -> Signals:
    n = b.n
    c = b.mid
    h = (b.bh + b.ah) * 0.5
    l = (b.bl + b.al) * 0.5
    A = atr(b, 14)
    Eb = ema(c, BIAS_EMA)

    kz = np.isin(b.hod, np.asarray(KZ_HOURS))
    min_in_hr = b.minute - b.hod.astype(np.int32) * 60
    in_or = kz & (min_in_hr < ORN)
    in_trade = kz & (min_in_hr >= ORN) & (min_in_hr < TRADE_END)

    volok = (A >= ATR_LO) & (A <= ATR_HI)
    bias_up = c > Eb
    bias_dn = c < Eb

    # group id per day+hour (monotonic non-decreasing over time -> contiguous groups)
    gid = b.day * 24 + b.hod.astype(np.int64)
    bnd = np.concatenate(([0], np.where(np.diff(gid) != 0)[0] + 1, [n]))

    sig_i = []; sig_side = []; sig_sl = []

    for g in range(len(bnd) - 1):
        s, e = int(bnd[g]), int(bnd[g + 1])
        if not kz[s]:
            continue
        or_mask = in_or[s:e]
        if not or_mask.any():
            continue
        seg_h = h[s:e]; seg_l = l[s:e]
        or_hi = float(seg_h[or_mask].max())
        or_lo = float(seg_l[or_mask].min())
        width = or_hi - or_lo
        if width <= 0:
            continue

        # first qualifying break inside the trade window of THIS kill-zone
        best_idx = -1; best_side = 0; best_slp = 0.0
        for off in range(e - s):
            i = s + off
            if not in_trade[i] or not volok[i] or not np.isfinite(A[i]):
                continue
            wlo = OR_WMIN * A[i]; whi = OR_WMAX * A[i]
            if width < wlo or width > whi:
                continue
            disp = K_BRK * A[i]
            up = (c[i] - or_hi >= disp) and bias_up[i] and (SIDE >= 0)
            dn = (or_lo - c[i] >= disp) and bias_dn[i] and (SIDE <= 0)
            if up:
                slp = KSL * A[i] if KSL > 0 else (c[i] - or_lo) + BUF_ATR * A[i]
                if SL_MIN <= slp <= SL_MAX:
                    best_idx = i; best_side = 1; best_slp = slp; break
            elif dn:
                slp = KSL * A[i] if KSL > 0 else (or_hi - c[i]) + BUF_ATR * A[i]
                if SL_MIN <= slp <= SL_MAX:
                    best_idx = i; best_side = -1; best_slp = slp; break
        if best_idx >= 0:
            sig_i.append(best_idx); sig_side.append(best_side); sig_sl.append(best_slp)

    if not sig_i:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array(sig_i, np.int64)
    side = np.array(sig_side, np.int64)
    sl_pts = np.array(sig_sl, np.float64)
    tp_pts = (RR * sl_pts) if RR > 0 else np.full(len(i), np.inf)  # fixed target or trail-only
    level = np.zeros(len(i))                    # ignored for market
    ord_ = np.argsort(i, kind="stable")
    i, side, sl_pts, tp_pts, level = i[ord_], side[ord_], sl_pts[ord_], tp_pts[ord_], level[ord_]
    return Signals(i=i, side=side, kind=np.zeros(len(i), int), level=level,
                   sl_pts=sl_pts, tp_pts=tp_pts, ttl=np.zeros(len(i), np.int64))
