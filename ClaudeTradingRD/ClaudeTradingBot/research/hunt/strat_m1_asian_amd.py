"""Asian-range sweep -> London expansion (AMD) on M1 (TF=60).

MECHANISM (ICT AMD: Accumulation / Manipulation / Distribution)
---------------------------------------------------------------
1. ACCUMULATION: build the Asian-session range (00:00-06:00 UTC) high/low. This
   completes BEFORE the trade window, so referencing it during London/NY is causal.
2. MANIPULATION: at/after the London open, one side of the Asian range is SWEPT --
   price trades beyond asian_hi (buy-side grab) or below asian_lo (sell-side grab),
   taking the resting liquidity.
3. DISTRIBUTION: price DISPLACES back through the swept level (a real body >= DISP*ATR,
   not a drift). We then do NOT chase; we rest a LIMIT at a retracement of the
   displacement leg (the textbook AMD entry) with a TIGHT stop just beyond the sweep
   extreme, and target the expansion toward the OPPOSITE side of the range.
   Long after a low-sweep+reclaim, short after a high-sweep+rejection.

WHY THE LIMIT-RETRACE ENTRY (vs market-chase)
---------------------------------------------
Entering at market on the displacement close chases the move: bad fill, wide stop,
avgloss > avgwin, and TRAIN goes negative on both sides (measured). The AMD edge, if
real, lives in the RETEST: rest a limit back into the reclaimed level so the stop can
sit just under the manipulation extreme (tight R) and the distribution leg pays multiple
R. This mirrors the repo's only proven survivors (OB-retest / FVG continuation, both
LIMIT-on-retrace, long-only, trend-gated). The limit is judged on the TAKER grid (enter
at market/stop when price returns to the level) so it stays deployable on FundingPips.

CAUSALITY
---------
- Asian range per UTC day is the max/min over hod in [ASIA_A, ASIA_B); every trade bar
  has hod >= TRADE hours which are strictly later in the SAME UTC day -> range fully
  formed, no look-ahead. Range mapped per-bar from the day's OWN asian window only.
- ATR is Wilder-causal (engine.atr). EMA bias is past-only (features.ema).
- The sweep state machine reads only bars <= i (running flags accumulate in time).
- Decision at bar i; the engine fills the LIMIT only on bars STRICTLY AFTER i
  (scan di+1..di+ttl) -- no future peek; the level is built from bars <= i.

HONEST RESULT (DEAD-END) -- measured on the runner + a full-history 0.25-taker per-year check
--------------------------------------------------------------------------------------------
Judged at the primary 0.25 TAKER spread (the deployable FundingPips case), the AMD family
is a REGIME-TILT artifact, not an edge. The faithful BOTH-SIDED mechanism loses in TRAIN
*and* OOS; the only OOS-positive slices come from isolating the LONG side, which merely
fits gold's 2026 up-leg on a tiny sample -- 2024 and 2025 stay negative.

  Full 30mo @0.25 taker, per calendar year (research/hunt/_amd_yr.py):
    market long  trail : 2024 pf0.48  2025 pf0.67  2026 pf2.56(n=2)   ALL net -$135
    market both  trail : 2024 pf0.53  2025 pf0.80  2026 pf0.89        ALL net -$324
    limit  long  trail : 2024 pf0.60  2025 pf0.98  2026 pf1.60        ALL net  -$16
  Runner (default split; 0.25t interpolated from the 0.20/0.30 taker grid):
    market both trail (this default): TR tk30 0.56 ; OOS N54 pf0.64 tk30 0.61 ; stress -$98
    market long trail               : TR tk30 0.44 ; OOS N13 tk30 1.59 ; stress +$6.8 (N far <100)
    limit  long trail               : TR tk30 0.61 ; OOS N20 tk30 1.56 ; stress +$2.6 (N far <100)

WHY IT FAILS (consistent with the repo's documented dead-ends)
  * The sweep->reclaim entry is a REVERSAL/expansion play; every mean-revert/expansion family
    on XAU dies at the cost floor and is train-negative. Displacement gating and a tight
    stop-above-the-sweep help RR but do not invert the sign in 2024-25.
  * Entering at market on the displacement bar CHASES the move; entering on a limit retrace
    fills so rarely (~1 setup/day, OOS N~20) that it is untestable and still train-negative.
  * The lone positive line is LONG-only in 2026 -- a regime fit, failing "positive every year".
  * Frequency is ~1.0-1.3 trades/day, below the 3-25/day band (widening the kill-zone to
    London+NY did not lift it past the single-position occupancy wall).
VERDICT: dead-end. Kept on disk with the exact numbers so later phases don't re-walk it.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF=60.
RUN: .venv/Scripts/python.exe -m bot.micro.runner research/hunt/strat_m1_asian_amd.py
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import ema, hours_mask


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "AMD_asian_sweep_london_expansion_m1"
TF = _P("AMD_TF", 60, int)                 # M1

# ---- Asian accumulation window (UTC hours, [A,B) ) ----
ASIA_A = _P("AMD_ASIA_A", 0, int)
ASIA_B = _P("AMD_ASIA_B", 6, int)
# ---- trade / kill-zone window (UTC hours list): London open + expansion into NY ----
TRADE_HOURS = tuple(int(x) for x in
                    os.environ.get("AMD_HOURS", "7,8,9,10,11,12,13,14").split(","))

DISP    = _P("AMD_DISP", 0.8)             # reclaim body must be >= DISP*ATR (displacement)
BUF     = _P("AMD_BUF", 0.5)             # stop buffer beyond the sweep extreme, in ATR
RETR    = _P("AMD_RETR", 0.5)            # limit retrace fraction of displacement leg (0..1)
SL_MIN  = _P("AMD_SLMIN", 1.0)
SL_MAX  = _P("AMD_SLMAX", 14.0)
ATR_LO  = _P("AMD_ATRLO", 0.15)
ATR_HI  = _P("AMD_ATRHI", 30.0)
BIAS_EMA = _P("AMD_BIAS", 200, int)      # slow EMA trend bias on M1
SIDE    = _P("AMD_SIDE", 0, int)         # 0=both (faithful AMD), 1=long-only, -1=short-only
MAX_PER_SIDE = _P("AMD_MAXSIDE", 2, int) # setups per side per day
TTL     = _P("AMD_TTL", 40, int)         # M1 bars the limit stays live
KIND    = os.environ.get("AMD_KIND", "market")  # 'market' (enter expansion) or 'limit' (retrace)
TRAIL   = _P("AMD_TRAIL", 4.0)           # chandelier trail (pts); tp=inf -> trail-only exit
EXIT    = os.environ.get("AMD_EXIT", "trail")  # 'trail' or 'target' (opposite Asian side)
TGT_MULT = _P("AMD_TGTMULT", 1.0)        # target = TGT_MULT * distance to opposite side (target mode)
RR      = _P("AMD_RR", 3.0)              # cap target at RR*risk (target mode)

SIM = dict(maxhold=_P("AMD_MAXHOLD", 120, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("AMD_COOLDOWN", 0, int),
           trail_pts=(TRAIL if EXIT == "trail" else 0.0))


def _asian_range(b: Bars):
    """Per-bar Asian hi/lo for that bar's OWN UTC day. Causal for bars after ASIA_B.
    Vectorized: group bars by epoch-day, reduce hi/lo over that day's asian window only,
    then broadcast the day's range to every bar of the same day."""
    n = b.n
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    in_asia = (b.hod >= ASIA_A) & (b.hod < ASIA_B)
    # contiguous group id per bar (b.day is monotonic non-decreasing in the run)
    _, gid = np.unique(b.day, return_inverse=True)
    ndays = int(gid.max()) + 1 if n else 0
    ah = np.full(ndays, -np.inf)
    al = np.full(ndays, np.inf)
    if in_asia.any():
        np.maximum.at(ah, gid[in_asia], hi[in_asia])
        np.minimum.at(al, gid[in_asia], lo[in_asia])
    out_hi = ah[gid]
    out_lo = al[gid]
    out_hi = np.where(np.isfinite(out_hi), out_hi, np.nan)
    out_lo = np.where(np.isfinite(out_lo), out_lo, np.nan)
    return out_hi, out_lo


def generate(b: Bars) -> Signals:
    n = b.n
    c = b.mid
    o = (b.bo + b.ao) * 0.5
    h = (b.bh + b.ah) * 0.5
    l = (b.bl + b.al) * 0.5
    A = atr(b, 14)
    Eb = ema(c, BIAS_EMA)
    a_hi, a_lo = _asian_range(b)
    trade = hours_mask(b, TRADE_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)
    have_range = np.isfinite(a_hi) & np.isfinite(a_lo)
    bias_up = c > Eb
    bias_dn = c < Eb

    sig_i = []; sig_side = []; sig_level = []; sig_sl = []; sig_tp = []

    idx = np.where(trade & have_range & volok & np.isfinite(A))[0]

    cur_day = -1
    swept_low = False; low_ext = np.inf
    swept_high = False; high_ext = -np.inf
    n_long = 0; n_short = 0

    for i in idx:
        dd = int(b.day[i])
        if dd != cur_day:
            cur_day = dd
            swept_low = False; low_ext = np.inf
            swept_high = False; high_ext = -np.inf
            n_long = 0; n_short = 0

        ahi = a_hi[i]; alo = a_lo[i]

        # --- manipulation: track sweeps (running, causal) ---
        if l[i] < alo:
            swept_low = True
            if l[i] < low_ext:
                low_ext = l[i]
        if h[i] > ahi:
            swept_high = True
            if h[i] > high_ext:
                high_ext = h[i]

        body = c[i] - o[i]
        disp = DISP * A[i]

        mkt = (KIND == "market")

        # --- LONG: low swept, bullish displacement reclaim above asian_lo ---
        if (SIDE >= 0) and swept_low and n_long < MAX_PER_SIDE and bias_up[i]:
            if (c[i] > alo) and (body >= disp):
                # limit retrace back down toward the sweep low (or market at close)
                level = c[i] if mkt else c[i] - RETR * (c[i] - low_ext)
                sl = low_ext - BUF * A[i]
                sl_pts = level - sl
                if EXIT == "trail":
                    tp_pts = np.inf
                else:
                    tp_pts = min(TGT_MULT * (ahi - level), RR * sl_pts)
                if (SL_MIN <= sl_pts <= SL_MAX) and (tp_pts > 0) and (mkt or level < c[i]):
                    sig_i.append(int(i)); sig_side.append(1); sig_level.append(level)
                    sig_sl.append(sl_pts); sig_tp.append(tp_pts)
                    n_long += 1

        # --- SHORT: high swept, bearish displacement rejection below asian_hi ---
        if (SIDE <= 0) and swept_high and n_short < MAX_PER_SIDE and bias_dn[i]:
            if (c[i] < ahi) and (-body >= disp):
                level = c[i] if mkt else c[i] + RETR * (high_ext - c[i])
                sl = high_ext + BUF * A[i]
                sl_pts = sl - level
                if EXIT == "trail":
                    tp_pts = np.inf
                else:
                    tp_pts = min(TGT_MULT * (level - alo), RR * sl_pts)
                if (SL_MIN <= sl_pts <= SL_MAX) and (tp_pts > 0) and (mkt or level > c[i]):
                    sig_i.append(int(i)); sig_side.append(-1); sig_level.append(level)
                    sig_sl.append(sl_pts); sig_tp.append(tp_pts)
                    n_short += 1

    if not sig_i:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array(sig_i, np.int64)
    side = np.array(sig_side, np.int64)
    level = np.array(sig_level, np.float64)
    sl_pts = np.array(sig_sl, np.float64)
    tp_pts = np.array(sig_tp, np.float64)
    kind = (np.zeros(len(i), np.int64) if KIND == "market"
            else np.ones(len(i), np.int64))   # 0=market/taker ; 1=limit(maker, taker-repriced)
    ord_ = np.argsort(i, kind="stable")
    return Signals(i=i[ord_], side=side[ord_], kind=kind[ord_], level=level[ord_],
                   sl_pts=sl_pts[ord_], tp_pts=tp_pts[ord_],
                   ttl=np.full(len(i), TTL, np.int64))
