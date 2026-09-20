"""Equal-highs / equal-lows LIQUIDITY POOL RAID (reversal) -- M1 (TF=60).

FAMILY
------
A liquidity pool is a cluster of >=2 CONFIRMED fractal swing highs (or lows)
resting at ~the same price (within EQ_TOL*ATR). Retail/stop liquidity pools just
beyond that shelf. The ICT "raid" = price SWEEPS beyond the pool (takes the
liquidity) on one M1 bar and then REJECTS -- closing back on the origin side of
the pool in the same bar. That failed sweep is the reversal trigger:
  equal-HIGHS swept + rejected  -> SHORT (fade the failed breakout up)
  equal-LOWS  swept + rejected  -> LONG  (fade the failed breakdown)
Kill-zone gated to London+NY. Structure stop beyond the sweep extreme; exit
either fixed RR or chandelier trail.

CAUSALITY (audited)
-------------------
* Swings come from features.swings() which is CENTERED (fractal half-width
  SWING_K). A swing at bar j is only KNOWABLE at bar j+SWING_K, so it is added to
  the active pool set exactly at i = j+SWING_K (never read early).
* Pool level = max/min of a cluster of swing highs/lows all confirmed by <= i.
* ATR (Wilder) and EMA are causal (engine.atr / features.ema).
* The raid decision is taken at bar i using only bar<=i info (h[i],l[i],c[i] and
  the already-confirmed pool). Entry is kind=0 MARKET -> engine fills at bar i+1
  open (taker), so nothing hindsight-priced. sl_pts/tp_pts are DISTANCES.
* No future indexing anywhere; the only forward object is the engine's own fill.

TAKER NOTE: FundingPips MT5 is market-execution/taker-only, so entries are market
(kind=0) and the honest metric is the oos_spread_grid 0.25 TAKER block.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF=60.
RUN: .venv/Scripts/python.exe -m bot.micro.runner research/hunt/strat_m1_eqhl_raid.py
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import swings, hours_mask, ema


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "EQHL_raid_m1"
TF = _P("EQ_TF", 60, int)

SWING_K   = _P("EQ_SWK", 2, int)        # fractal half-width for swings
LOOKBACK  = _P("EQ_LB", 180, int)       # bars a swing stays eligible for a pool (~3h M1)
EQ_TOL    = _P("EQ_TOL", 0.15)          # equal tolerance as fraction of ATR (truly equal)
MIN_SEP   = _P("EQ_SEP", 5, int)        # min bars between the two equal swings (real shelf)
POOL_TTL  = _P("EQ_POOLTTL", 90, int)   # bars a formed pool stays armed for a raid
SWEEP     = _P("EQ_SWEEP", 0.05)        # min poke beyond pool as fraction of ATR
REJ       = _P("EQ_REJ", 0.05)          # min close-back inside pool as fraction of ATR
WICK      = _P("EQ_WICK", 0.55)         # rejection: close in favorable frac of the raid-bar range
BUF_ATR   = _P("EQ_BUF", 0.30)          # stop buffer beyond the sweep extreme, in ATR
RR        = _P("EQ_RR", 1.6)            # reward:risk for fixed-target mode
TP_MODE   = os.environ.get("EQ_TPMODE", "rr")   # "rr" or "trail"
TRAIL     = _P("EQ_TRAIL", 3.0)
MAXHOLD   = _P("EQ_MAXHOLD", 60, int)
ATR_LO    = _P("EQ_ATRLO", 0.15)
ATR_HI    = _P("EQ_ATRHI", 20.0)
SL_MIN    = _P("EQ_SLMIN", 0.6)
SL_MAX    = _P("EQ_SLMAX", 12.0)
SIDE      = _P("EQ_SIDE", 1, int)       # 0=both, 1=long-only, -1=short-only
BIAS_EMA  = _P("EQ_BIAS", 0, int)       # 0=off; else require reversal aligned toward EMA
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("EQ_HOURS", "7,8,9,10,11,12,13,14,15,16").split(","))

_trail_on = (TP_MODE == "trail")
SIM = dict(maxhold=MAXHOLD, dollars_per_point=1.0, commission=0.07,
           cooldown=_P("EQ_COOLDOWN", 0, int),
           trail_pts=(TRAIL if _trail_on else 0.0))


def generate(b: Bars) -> Signals:
    n = b.n
    c = b.mid
    h = (b.bh + b.ah) * 0.5
    l = (b.bl + b.al) * 0.5
    A = atr(b, 14)
    sh, sl = swings(h, l, SWING_K)
    sess = hours_mask(b, SESSION_HOURS)
    volok = np.isfinite(A) & (A >= ATR_LO) & (A <= ATR_HI)
    if BIAS_EMA > 0:
        E = ema(c, BIAS_EMA)
    else:
        E = None

    sig_i = []; sig_side = []; sig_sl = []; sig_tp = []

    # active confirmed swing lists: (bar_idx, level)
    sw_hi = []   # swing highs
    sw_lo = []   # swing lows
    pool_hi = None; pool_hi_at = -1   # (level) equal-high liquidity shelf
    pool_lo = None; pool_lo_at = -1

    for i in range(n):
        j = i - SWING_K
        if j >= 0:
            if sh[j]:
                sw_hi.append((j, h[j]))
            if sl[j]:
                sw_lo.append((j, l[j]))
        # purge stale swings
        lo_edge = i - LOOKBACK
        if sw_hi and sw_hi[0][0] < lo_edge:
            sw_hi = [(x, v) for x, v in sw_hi if x >= lo_edge]
        if sw_lo and sw_lo[0][0] < lo_edge:
            sw_lo = [(x, v) for x, v in sw_lo if x >= lo_edge]

        Ai = A[i]
        if not np.isfinite(Ai) or Ai <= 0:
            continue
        tol = EQ_TOL * Ai

        # (re)form an equal-high pool: most recent swing high must have a peer
        # swing high within tol AND at least MIN_SEP bars earlier (a real shelf,
        # a double/triple top, not two adjacent fractals).
        if len(sw_hi) >= 2:
            last_idx, last_lvl = sw_hi[-1]
            cluster = [v for x, v in sw_hi
                       if abs(v - last_lvl) <= tol and (last_idx - x) >= MIN_SEP]
            if cluster:
                lvl = max(cluster + [last_lvl])
                if pool_hi is None or abs(lvl - pool_hi) > tol:
                    pool_hi = lvl; pool_hi_at = i
        if len(sw_lo) >= 2:
            last_idx, last_lvl = sw_lo[-1]
            cluster = [v for x, v in sw_lo
                       if abs(v - last_lvl) <= tol and (last_idx - x) >= MIN_SEP]
            if cluster:
                lvl = min(cluster + [last_lvl])
                if pool_lo is None or abs(lvl - pool_lo) > tol:
                    pool_lo = lvl; pool_lo_at = i

        # expire pools
        if pool_hi is not None and (i - pool_hi_at) > POOL_TTL:
            pool_hi = None
        if pool_lo is not None and (i - pool_lo_at) > POOL_TTL:
            pool_lo = None

        if not sess[i] or not volok[i]:
            continue

        # ---- SHORT raid: sweep above equal-highs, reject back below ----
        if pool_hi is not None and (SIDE == 0 or SIDE == -1):
            rng = h[i] - l[i]
            wick_ok = rng > 0 and (h[i] - c[i]) / rng >= WICK
            if h[i] > pool_hi + SWEEP * Ai and c[i] < pool_hi - REJ * Ai and wick_ok:
                bias_ok = True if E is None else (c[i] < E[i])
                if bias_ok:
                    sl_price = h[i] + BUF_ATR * Ai
                    sl_pts = sl_price - c[i]
                    if SL_MIN <= sl_pts <= SL_MAX:
                        sig_i.append(i); sig_side.append(-1)
                        sig_sl.append(sl_pts)
                        sig_tp.append(np.inf if _trail_on else RR * sl_pts)
                pool_hi = None  # consume

        # ---- LONG raid: sweep below equal-lows, reject back above ----
        if pool_lo is not None and (SIDE == 0 or SIDE == 1):
            rng = h[i] - l[i]
            wick_ok = rng > 0 and (c[i] - l[i]) / rng >= WICK
            if l[i] < pool_lo - SWEEP * Ai and c[i] > pool_lo + REJ * Ai and wick_ok:
                bias_ok = True if E is None else (c[i] > E[i])
                if bias_ok:
                    sl_price = l[i] - BUF_ATR * Ai
                    sl_pts = c[i] - sl_price
                    if SL_MIN <= sl_pts <= SL_MAX:
                        sig_i.append(i); sig_side.append(1)
                        sig_sl.append(sl_pts)
                        sig_tp.append(np.inf if _trail_on else RR * sl_pts)
                pool_lo = None  # consume

    if not sig_i:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array(sig_i, np.int64)
    side = np.array(sig_side, np.int64)
    sl_pts = np.array(sig_sl, np.float64)
    tp_pts = np.array(sig_tp, np.float64)
    m = len(i)
    return Signals(i=i, side=side, kind=np.zeros(m, int),
                   level=np.zeros(m), sl_pts=sl_pts, tp_pts=tp_pts,
                   ttl=np.full(m, 1, np.int64))
