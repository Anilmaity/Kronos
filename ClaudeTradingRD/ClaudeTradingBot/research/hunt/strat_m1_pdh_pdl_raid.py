"""Prior-day High / Low LIQUIDITY RAID -- M1 (TF=60).

FAMILY (assigned)
-----------------
The prior-day high (PDH) and prior-day low (PDL) are the day's most-watched resting
liquidity: buy-stops sit above PDH, sell-stops below PDL. In the London/NY kill zone
price often RAIDS one of them (pokes beyond, taking the liquidity). Two archetypes:

  FADE  (reversal): price sweeps beyond the level then REJECTS -- closes back inside
        the prior-day range on the same bar. The failed sweep is a reversal trigger.
        PDL swept + reclaimed  -> LONG (fade the failed breakdown, back into range)
        PDH swept + rejected   -> SHORT (fade the failed breakout)
        Aligned with HTF bias: a PDL sweep in an uptrend that reclaims is a with-trend
        long; a PDH sweep in a downtrend that rejects is a with-trend short.

  CONT  (continuation): price CLOSES decisively beyond the level with HTF bias
        agreeing -> expansion out of the range.
        close > PDH + bias_up  -> LONG      close < PDL + bias_dn -> SHORT

Kill-zone gated (London+NY). Structure stop beyond the sweep extreme (fade) or an
ATR stop (cont). Exit fixed RR or chandelier trail. Each PDH/PDL level is CONSUMED
after one raid per day so we do not re-fire the same shelf. Both modes are exposed;
the runner decides which (if any) carries a real 0.25-taker edge.

CAUSALITY (audited, no look-ahead)
----------------------------------
* PDH/PDL are the high/low of the PREVIOUS distinct trading UTC day. Because the bar
  array is time-ordered and b.day is monotone non-decreasing, ALL bars of day d-1
  precede every bar of day d, so the prior-day extremes are fully formed and knowable
  before any bar that uses them. (Prior-day arrays are built by shifting the per-day
  reduce by exactly one day.)
* The raid decision at bar i uses only h[i],l[i],c[i] and the already-completed
  prior-day levels. Entry is kind=0 MARKET -> engine fills at bar i+1 open (taker);
  nothing is hindsight-priced. sl_pts/tp_pts are DISTANCES from the fill.
* ATR (Wilder) and EMA are causal. No future bar is indexed.

TAKER NOTE: the funded account (FundingPips MT5, acct 6c7ce166) is market-execution /
taker-only, so entries are MARKET (kind=0) and the honest metric is the
oos_spread_grid 0.25 TAKER block (conservative: a market entry pays ~full spread in
the maker column and is stressed a further +s in the taker column).

VERDICT (honest, tested through the runner at 0.25 taker) -- DEAD-END
--------------------------------------------------------------------
No configuration clears the acceptance bar. Two independent failures:

1. FREQUENCY WALL. PDH and PDL are only TWO levels/day; each is raided ~once. With
   any real edge-preserving filter, fills collapse to ~0.2-0.3 trades/day (OOS: 72
   trades over ~230 days) -- ~10x below the 2-4/day target and below even the repo's
   documented ~1.4/day XAU ceiling. Loosening to reach frequency turns the trigger
   into the bare breakout/sweep the repo already proved has NO directional edge.

2. EVERY EDGE-BEARING VARIANT IS REGIME-TILTED, NOT A PLATEAU. Numbers @0.25 taker:
     fade  (reversal, both/long/short, trail or rr, bias on/off): PF 0.44-0.61 -- all
           net-NEGATIVE. Fading PDH/PDL on M1 dies at the cost floor, as documented.
     cont  (bare close beyond level):                             PF 0.57-0.69 -- noise.
     contlim (displacement>=1.2*ATR close beyond level -> LIMIT retest + chandelier):
           the ONLY positive branch. Best = both-sides, trail, EMA100 bias:
             OOS   0.25t PF ~2.0 (N=72)  ; stress PF 1.26 (+$23)
             TRAIN 0.20t PF 0.84 / 0.30t 0.71  -> TRAIN-NEGATIVE at taker
             per-year: 2024 PF 0.66 (NEG) ; 2025 1.65 ; 2026 1.79
           i.e. a 2025-26 regime fit (same failure mode as EDGE_microbos / r2_0 /
           r3_5): strong OOS but negative in TRAIN and in 2024, so it FAILS the
           "positive @0.25 taker in TRAIN and every calendar year" robustness gate.

Defaults below reproduce that best (still-failing) contlim config so the result is
re-runnable. This is a well-characterised negative: the prior-day-raid family does
not yield a live, train-robust, adequately-frequent XAUUSD edge.

CONTRACT: generate(b)->Signals ; SIM ; NAME ; TF=60.
RUN: .venv/Scripts/python.exe -m bot.micro.runner research/hunt/strat_m1_pdh_pdl_raid.py
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import hours_mask, ema


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


NAME = "PDH_PDL_raid_m1"
TF = _P("PD_TF", 60, int)

MODE      = os.environ.get("PD_MODE", "contlim")  # "fade" (reversal) / "cont" / "contlim"
K_DISP    = _P("PD_KDISP", 1.2)                   # contlim: displacement floor |c-o|>=K*ATR on break bar
PEN       = _P("PD_PEN", 0.0)                     # contlim: retest penetration past level (frac ATR)
TTL       = _P("PD_TTL", 30, int)                 # contlim: limit live bars
SIDE      = _P("PD_SIDE", 0, int)                 # 0=both, 1=long-only, -1=short-only
SWEEP     = _P("PD_SWEEP", 0.10)                  # min poke beyond level (fraction of ATR)
REJ       = _P("PD_REJ", 0.05)                    # min close-back inside (fade) / beyond (cont), frac ATR
BUF_ATR   = _P("PD_BUF", 0.30)                    # stop buffer beyond sweep extreme, in ATR
K_STOP    = _P("PD_KSTOP", 1.20)                  # ATR stop distance for CONT mode
RR        = _P("PD_RR", 1.6)                      # reward:risk for fixed-target mode
TP_MODE   = os.environ.get("PD_TPMODE", "trail")  # "rr" or "trail"
TRAIL     = _P("PD_TRAIL", 3.0)
MAXHOLD   = _P("PD_MAXHOLD", 60, int)
ATR_LO    = _P("PD_ATRLO", 0.15)
ATR_HI    = _P("PD_ATRHI", 20.0)
SL_MIN    = _P("PD_SLMIN", 0.6)
SL_MAX    = _P("PD_SLMAX", 14.0)
BIAS_EMA  = _P("PD_BIAS", 100, int)               # slow EMA trend bias on M1 close; 0=off
RAID_CAP  = _P("PD_RAIDCAP", 1, int)              # max raids per level per day
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("PD_HOURS", "7,8,9,10,11,12,13,14,15,16").split(","))

_trail_on = (TP_MODE == "trail")
SIM = dict(maxhold=MAXHOLD, dollars_per_point=1.0, commission=0.07,
           cooldown=_P("PD_COOLDOWN", 0, int),
           trail_pts=(TRAIL if _trail_on else 0.0))


def _prior_day_levels(b: Bars, h, l):
    """pdh[i], pdl[i] = high/low of the PREVIOUS distinct trading day. Causal."""
    day = b.day
    n = b.n
    # segment boundaries (day is monotone non-decreasing in a time-ordered feed)
    ud, first = np.unique(day, return_index=True)
    bounds = np.append(first, n)
    K = len(ud)
    day_hi = np.empty(K); day_lo = np.empty(K)
    for k in range(K):
        s, e = bounds[k], bounds[k + 1]
        day_hi[k] = h[s:e].max(); day_lo[k] = l[s:e].min()
    pdh_of = np.full(K, np.nan); pdl_of = np.full(K, np.nan)
    pdh_of[1:] = day_hi[:-1]; pdl_of[1:] = day_lo[:-1]
    pdh = np.empty(n); pdl = np.empty(n)
    for k in range(K):
        s, e = bounds[k], bounds[k + 1]
        pdh[s:e] = pdh_of[k]; pdl[s:e] = pdl_of[k]
    return pdh, pdl


def generate(b: Bars) -> Signals:
    n = b.n
    c = b.mid
    h = (b.bh + b.ah) * 0.5
    l = (b.bl + b.al) * 0.5
    A = atr(b, 14)
    E = ema(c, BIAS_EMA) if BIAS_EMA > 0 else None
    sess = hours_mask(b, SESSION_HOURS)
    volok = np.isfinite(A) & (A >= ATR_LO) & (A <= ATR_HI)
    pdh, pdl = _prior_day_levels(b, h, l)

    sig_i = []; sig_side = []; sig_sl = []; sig_tp = []
    sig_lvl = []; sig_kind = []
    o = (b.bo + b.ao) * 0.5

    cur_day = -1
    hi_raids = 0   # raids consumed at PDH this day
    lo_raids = 0

    for i in range(n):
        d = b.day[i]
        if d != cur_day:
            cur_day = d; hi_raids = 0; lo_raids = 0
        if not sess[i] or not volok[i]:
            continue
        Ai = A[i]
        ph = pdh[i]; pl = pdl[i]

        def emit(side, sl_pts, kind=0, level=0.0):
            if not (SL_MIN <= sl_pts <= SL_MAX):
                return
            sig_i.append(i); sig_side.append(side); sig_sl.append(sl_pts)
            sig_tp.append(np.inf if _trail_on else RR * sl_pts)
            sig_kind.append(kind); sig_lvl.append(level)

        if MODE == "fade":
            # ---- SHORT: sweep above PDH, reject back below ----
            if (SIDE == 0 or SIDE == -1) and hi_raids < RAID_CAP and np.isfinite(ph):
                if h[i] > ph + SWEEP * Ai and c[i] < ph - REJ * Ai:
                    if E is None or c[i] < E[i]:
                        emit(-1, (h[i] + BUF_ATR * Ai) - c[i])
                    hi_raids += 1
            # ---- LONG: sweep below PDL, reclaim back above ----
            if (SIDE == 0 or SIDE == 1) and lo_raids < RAID_CAP and np.isfinite(pl):
                if l[i] < pl - SWEEP * Ai and c[i] > pl + REJ * Ai:
                    if E is None or c[i] > E[i]:
                        emit(1, c[i] - (l[i] - BUF_ATR * Ai))
                    lo_raids += 1

        elif MODE == "cont":
            # ---- LONG: close decisively above PDH, uptrend ----
            if (SIDE == 0 or SIDE == 1) and hi_raids < RAID_CAP and np.isfinite(ph):
                if c[i] > ph + REJ * Ai:
                    if E is None or c[i] > E[i]:
                        emit(1, K_STOP * Ai)
                    hi_raids += 1
            # ---- SHORT: close decisively below PDL, downtrend ----
            if (SIDE == 0 or SIDE == -1) and lo_raids < RAID_CAP and np.isfinite(pl):
                if c[i] < pl - REJ * Ai:
                    if E is None or c[i] < E[i]:
                        emit(-1, K_STOP * Ai)
                    lo_raids += 1

        else:  # contlim: displacement break beyond PD level -> LIMIT retest of the level
            disp = abs(c[i] - o[i]) >= K_DISP * Ai
            # ---- LONG: displacement close above PDH, retest limit at PDH ----
            if (SIDE == 0 or SIDE == 1) and hi_raids < RAID_CAP and np.isfinite(ph):
                if c[i] > ph + REJ * Ai and disp and (E is None or c[i] > E[i]):
                    level = ph + PEN * Ai
                    stop = ph - BUF_ATR * Ai
                    if level < c[i]:
                        emit(1, level - stop, kind=1, level=level)
                    hi_raids += 1
            # ---- SHORT: displacement close below PDL, retest limit at PDL ----
            if (SIDE == 0 or SIDE == -1) and lo_raids < RAID_CAP and np.isfinite(pl):
                if c[i] < pl - REJ * Ai and disp and (E is None or c[i] < E[i]):
                    level = pl - PEN * Ai
                    stop = pl + BUF_ATR * Ai
                    if level > c[i]:
                        emit(-1, stop - level, kind=1, level=level)
                    lo_raids += 1

    if not sig_i:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array(sig_i, np.int64)
    side = np.array(sig_side, np.int64)
    sl_pts = np.array(sig_sl, np.float64)
    tp_pts = np.array(sig_tp, np.float64)
    kind = np.array(sig_kind, np.int64)
    level = np.array(sig_lvl, np.float64)
    m = len(i)
    ttl = np.where(kind == 1, TTL, 1).astype(np.int64)
    order = np.argsort(i, kind="stable")
    return Signals(i=i[order], side=side[order], kind=kind[order],
                   level=level[order], sl_pts=sl_pts[order], tp_pts=tp_pts[order],
                   ttl=ttl[order])
