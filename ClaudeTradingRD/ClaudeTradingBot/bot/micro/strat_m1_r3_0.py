"""M1 BIAS-ALIGNED LIQUIDITY-SWEEP REVERSAL (displacement-confirmed MSS retest).

WHY THIS IS NOT THE DEAD m1_session_sweep_revert FADE:
  The prior session-sweep attempt FADED the Asian high/low counter-trend and died
  (train-negative, regime fit) -- FINDINGS.md says the XAU edge lives in CONTINUATION,
  not in fading. This strategy keeps the *liquidity-sweep reversal* idea but turns it
  into a WITH-TREND smart-money entry:

    - HTF bias UP   -> we only take the sweep of a session LOW (sell-side liquidity
      grab below) that then DISPLACES back up = a failed breakdown / spring -> LONG.
      This is the ICT discount entry: buy after stops are run, in the direction of bias.
    - HTF bias DOWN -> only the sweep of a session HIGH that displaces back down -> SHORT.

  Two filters the fade lacked and that target excursion ASYMMETRY (scout #2/#3):
    (1) DISPLACEMENT: the reclaim bar must be an impulsive bar (|c-o| >= DISP*ATR)
        closing back through the swept level -- a real market-structure shift, not a wick.
    (2) BIAS ALIGNMENT: the reversal must agree with the M1 EMA-fast/EMA-slow trend, so
        we are continuing the dominant flow, never knife-catching it.

  Liquidity pool = the *session* extreme (Asian range, 00:00-06:59 UTC) -- genuine
  resting liquidity London/NY hunt -- plus an optional prior-day level. First sweep of
  each side per day only (freshness). M1 (~2pt) gives the retest room to clear cost.

ENTRY: maker limit RETEST at the swept level (KIND=1, taker-efficient: one spread cross
  in the taker grid). Stop beyond the sweep extreme; target = TP_R * stop directed into
  the range interior (measured move).

NO LOOK-AHEAD: Asian range for a UTC day is built only from hod in [0,7) and read only
  at hod>=7 (all Asian bars precede every trade bar that day). Prior-day H/L use only
  completed prior days. ATR + EMA are causal recursions. Signals fire on the displacement
  bar; the engine fills the limit on a LATER bar. No centered/future index is read.
CONTRACT: generate(b)->Signals, SIM, NAME, TF=60.

HONEST VERDICT (round-3, NOT a survivor): this concept does NOT clear the strict bar.
  The default config below is the CLOSEST honest representative; it is TRAIN-NEGATIVE.
    train 0.25-taker grid PF ~0.84 (0.868@0.20 / 0.803@0.30)  -- below the 1.15 bar
    oos   0.25-taker grid PF ~1.03 (1.145@0.20 / 0.916@0.30)  -- only marginally >1
    OOS trades = 29 (~1.07/day) -- far below the >=100 / 3-20/day requirement.
  A full sweep of the family was run (entry: limit-at-level / market / retest-into-
  displacement; exit: fixed TP_R 1.0-3.0 / trailing 0.8-1.6; structure: BOS on/off;
  bias: EMA 20/80..60/240 / none; frequency: first-per-day on/off, +prior-day levels;
  both sides). TRAIN 0.25-taker PF CAPS AT ~0.84 everywhere -- it is never positive.
  The long and short sides are regime-MIRRORED (long better in the 2024-25 uptrend OOS,
  short better in train) -- the definitive signature of REGIME FIT, not a real edge.
  This reproduces the prior m1_session_sweep_revert dead end and research/FINDINGS.md:
  the XAU M1 liquidity-sweep REVERSAL has no train-robust taker edge; the only robust
  M1 taker edges found are CONTINUATION (m1_fvg_cont_bias_gapfloor, ob_retest_cont_m5).
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr as atr_fn, roll_max, roll_min
from bot.micro.features import hours_mask, ema

NAME = "m1_bias_sweep_reversal"
TF = 60   # M1


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


KIND      = _P("BR_KIND", 1, int)        # 0=market on displacement bar, 1=limit retest
TRAIL     = _P("BR_TRAIL", 0.0)          # trailing-stop pts (>0 -> trail+ride continuation)
_sim = dict(maxhold=_P("BR_MAXHOLD", 60, int), dollars_per_point=1.0, commission=0.07,
            cooldown=_P("BR_COOLDOWN", 2, int))
if TRAIL > 0:
    _sim["trail_pts"] = TRAIL
SIM = _sim
BOS_LB    = _P("BR_BOSLB", 0, int)       # displacement bar must break prior-N extreme (MSS); 0=off

ATR_P     = _P("BR_ATRP", 20, int)       # M1 ATR period
SWEEP_BUF = _P("BR_SWBUF", 0.25)         # sweep must exceed level by >= this * ATR
MAXPEN    = _P("BR_MAXPEN", 3.0)         # sweep pokes at most this * ATR beyond (marginal)
DISP      = _P("BR_DISP", 0.7)           # displacement bar body >= DISP * ATR
RECLAIM_K = _P("BR_RECK", 0.05)          # close must reclaim this * ATR past the level
EMA_F     = _P("BR_EMAF", 60, int)       # fast EMA (M1) for bias
EMA_S     = _P("BR_EMAS", 240, int)      # slow EMA (M1) for bias
SL_BUF    = _P("BR_SLBUF", 0.8)          # stop sits SL_BUF*ATR beyond the sweep extreme
TP_R      = _P("BR_TPR", 3.0)            # target = TP_R * stop distance (interior-directed)
RR_MIN    = _P("BR_RRMIN", 0.5)
RR_MAX    = _P("BR_RRMAX", 12.0)
RNG_LO    = _P("BR_RNGLO", 3.0)          # min Asian range (pts)
RNG_HI    = _P("BR_RNGHI", 50.0)         # max Asian range (pts)
ATR_LO    = _P("BR_ATRLO", 0.4)
ATR_HI    = _P("BR_ATRHI", 16.0)
SL_MIN    = _P("BR_SLMIN", 0.8)
SL_MAX    = _P("BR_SLMAX", 9.0)
TTL       = _P("BR_TTL", 8, int)         # retest limit lifetime (M1 bars), KIND=1 only
SIDE_ONLY = _P("BR_SIDE", 0, int)        # 0=both, 1=long-only, -1=short-only
USE_PDAY  = _P("BR_PDAY", 1, int)        # also sweep prior-day high/low
FIRST     = _P("BR_FIRST", 1, int)       # 1=only first sweep of each side per day
USE_BIAS  = _P("BR_USEBIAS", 1, int)     # 1=bias-align; 0=both sides regardless of trend
ASIA_A    = _P("BR_ASIA_A", 0, int)
ASIA_Z    = _P("BR_ASIA_Z", 7, int)
LEVEL_AT  = _P("BR_LVLAT", 0, int)       # 0=limit at swept level, 1=retest INTO displ body
FIB       = _P("BR_FIB", 0.5)            # retest penetration into displacement bar (LEVEL_AT=1)
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("BR_HOURS", "7,8,9,10,11,12,13,14").split(","))


def _session_range(b, hi, lo):
    n = b.n; day = b.day; hod = b.hod
    aH = np.full(n, np.nan); aL = np.full(n, np.nan)
    chg = np.concatenate(([0], np.where(np.diff(day) != 0)[0] + 1, [n]))
    for k in range(len(chg) - 1):
        s, e = int(chg[k]), int(chg[k + 1])
        m = (hod[s:e] >= ASIA_A) & (hod[s:e] < ASIA_Z)
        if m.any():
            aH[s:e] = hi[s:e][m].max()
            aL[s:e] = lo[s:e][m].min()
    return aH, aL


def _prior_day_hl(b, hi, lo):
    """Prior COMPLETED UTC day's high/low broadcast to every bar of the next day."""
    n = b.n; day = b.day
    pH = np.full(n, np.nan); pL = np.full(n, np.nan)
    chg = np.concatenate(([0], np.where(np.diff(day) != 0)[0] + 1, [n]))
    prevH = np.nan; prevL = np.nan
    for k in range(len(chg) - 1):
        s, e = int(chg[k]), int(chg[k + 1])
        if np.isfinite(prevH):
            pH[s:e] = prevH; pL[s:e] = prevL
        prevH = hi[s:e].max(); prevL = lo[s:e].min()
    return pH, pL


def _first_per_day(idx, day):
    if len(idx) == 0:
        return idx
    d = day[idx]
    keep = np.ones(len(idx), bool)
    keep[1:] = d[1:] != d[:-1]
    return idx[keep]


def _empty():
    z = np.zeros(0)
    return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)


def _sweep_long(base, lo, c, o, lvl, a):
    """sell-side sweep of `lvl` (a session low) + up-displacement reclaim -> LONG."""
    return base & np.isfinite(lvl) & (lo <= lvl - SWEEP_BUF * a) & (lo >= lvl - MAXPEN * a) \
        & (c >= lvl + RECLAIM_K * a) & ((c - o) >= DISP * a)


def _sweep_short(base, hi, c, o, lvl, a):
    return base & np.isfinite(lvl) & (hi >= lvl + SWEEP_BUF * a) & (hi <= lvl + MAXPEN * a) \
        & (c <= lvl - RECLAIM_K * a) & ((o - c) >= DISP * a)


def generate(b: Bars) -> Signals:
    n = b.n
    if n < 300:
        return _empty()
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    c  = b.mid
    o  = (b.ao + b.bo) * 0.5
    A  = atr_fn(b, ATR_P)
    a  = np.where(np.isfinite(A) & (A > 0), A, np.nan)

    ef = ema(c, EMA_F); es = ema(c, EMA_S)
    bias = np.sign(ef - es)

    # MSS / break-of-structure: displacement bar closes beyond prior-N extreme
    if BOS_LB > 0:
        phi = roll_max(hi, BOS_LB); plo = roll_min(lo, BOS_LB)
        bos_up = np.isfinite(phi) & (c > phi)
        bos_dn = np.isfinite(plo) & (c < plo)
    else:
        bos_up = np.ones(n, bool); bos_dn = np.ones(n, bool)

    aH, aL = _session_range(b, hi, lo)
    rng = aH - aL
    sess = hours_mask(b, SESSION_HOURS)
    volok = np.isfinite(a) & (a >= ATR_LO) & (a <= ATR_HI)
    rngok = np.isfinite(rng) & (rng >= RNG_LO) & (rng <= RNG_HI)
    base = sess & volok & rngok & np.isfinite(aH)

    levels_lo = [aL]
    levels_hi = [aH]
    if USE_PDAY:
        pH, pL = _prior_day_hl(b, hi, lo)
        levels_lo.append(pL); levels_hi.append(pH)

    longs = np.zeros(n, bool); shorts = np.zeros(n, bool)
    long_lvl = np.full(n, np.nan); short_lvl = np.full(n, np.nan)
    long_swext = np.full(n, np.nan); short_swext = np.full(n, np.nan)

    if USE_BIAS:
        biasup = base & (bias > 0) & bos_up
        biasdn = base & (bias < 0) & bos_dn
    else:
        biasup = base & bos_up
        biasdn = base & bos_dn
    for lv in levels_lo:
        m = _sweep_long(biasup, lo, c, o, lv, a)
        take = m & ~longs
        longs |= take
        long_lvl = np.where(take, lv, long_lvl)
        long_swext = np.where(take, lo, long_swext)
    for lv in levels_hi:
        m = _sweep_short(biasdn, hi, c, o, lv, a)
        take = m & ~shorts
        shorts |= take
        short_lvl = np.where(take, lv, short_lvl)
        short_swext = np.where(take, hi, short_swext)

    if SIDE_ONLY > 0:
        shorts[:] = False
    if SIDE_ONLY < 0:
        longs[:] = False

    iL = np.where(longs)[0]; iH = np.where(shorts)[0]
    if FIRST:
        iL = _first_per_day(iL, b.day); iH = _first_per_day(iH, b.day)
    if len(iL) + len(iH) == 0:
        return _empty()

    # entry level: retest INTO the displacement bar (favorable with-trend pullback)
    if LEVEL_AT == 1:
        lvL = c[iL] - FIB * (c[iL] - o[iL])      # buy a pullback into the up-displacement body
        lvH = c[iH] + FIB * (o[iH] - c[iH])      # sell a pullback into the down-displacement body
    elif KIND == 1:
        lvL = long_lvl[iL]; lvH = short_lvl[iH]  # retest at the swept session level
    else:
        lvL = c[iL]; lvH = c[iH]                 # market-style at displacement close

    # stop beyond sweep extreme
    slL = (lvL - long_swext[iL]) + SL_BUF * a[iL]
    slH = (short_swext[iH] - lvH) + SL_BUF * a[iH]
    if TRAIL > 0:
        tpL = np.full(len(iL), np.inf); tpH = np.full(len(iH), np.inf)
    else:
        tpL = TP_R * slL; tpH = TP_R * slH

    i = np.concatenate([iL, iH])
    side = np.concatenate([np.ones(len(iL), np.int64), -np.ones(len(iH), np.int64)])
    level = np.concatenate([lvL, lvH])
    slp = np.concatenate([slL, slH])
    tpp = np.concatenate([tpL, tpH])

    ok = (slp >= SL_MIN) & (slp <= SL_MAX) & (tpp > 0) & np.isfinite(level)
    if TRAIL <= 0:
        rr = tpp / np.where(slp > 0, slp, np.nan)
        ok = ok & np.isfinite(rr) & (rr >= RR_MIN) & (rr <= RR_MAX)
    i, side, level, slp, tpp = i[ok], side[ok], level[ok], slp[ok], tpp[ok]
    if len(i) == 0:
        return _empty()

    o2 = np.argsort(i, kind="stable")
    i, side, level, slp, tpp = i[o2], side[o2], level[o2], slp[o2], tpp[o2]
    m = len(i)
    return Signals(i=i, side=side, kind=np.full(m, KIND, np.int8), level=level,
                   sl_pts=slp, tp_pts=tpp, ttl=np.full(m, TTL, np.int64))
