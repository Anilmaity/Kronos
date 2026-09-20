"""Micro-BOS continuation, RETEST-FAMILY frequency push (round 3).

BASE: bot/micro/strat_r3_1.py (micro-BOS displacement continuation, MAKER retest,
trend-aligned, session-gated, ATR-banded, trailing exit). That base has a REAL but
THIN edge: OOS ~1.1 trades/day, PF 1.33 taker @0.20 / 1.10 taker @0.30. The round-2
gap is FREQUENCY: lift OOS trades toward the 3-25/day band (OOS N >= 100) while
holding PF >= 1.3 at 0.25 taker and positive at 0.30 taker.

MY LEVER = the RETEST entry mechanic. Instead of one shallow maker limit per fresh
break edge, I broaden the retest in two causal, no-look-ahead ways:

  1. CONTINUATION RE-ARM (more break EVENTS): the base fires only on the first bar of
     a break boolean. A trend keeps printing new structure highs/lows; each genuine
     new displacement extreme that advances the leg by >= REARM_STEP * M1-ATR beyond
     the last armed extreme is a fresh continuation context and re-arms a new retest
     order. This is the productive part of the prior cont_ladder line, kept tight.

  2. RETEST LADDER (more FILLS per event): for each armed event place up to three
     maker limits at different depths of the SAME leg --
        A. shallow retest  : extreme_broken - RETR_A * disp   (closest, fills often)
        B. breaker level    : the broken structure level itself (classic breaker retest)
        C. deeper 2nd-chance: extreme_broken - RETR_C * disp   (rare deep pullback)
     One position at a time means at most one of A/B/C fills per event; the ladder
     raises the FILL PROBABILITY of each real continuation context rather than the
     number of concurrent trades, which is exactly the frequency we want without
     diluting the directional filter.

All gates (session, EMA bias, ATR band, displacement >= K*ATR) are unchanged so the
directional edge that survives cost is preserved. Params overridable via env (MB_*)
for the sweep; the committed defaults are the honest plateau center.

HONEST RESULT (this is the deliverable, not a pass). Real S5 ticks, train 2024-01..
2025-07, OOS 2025-08..2026-06; PRIMARY judge = 0.25 taker PF (interp of 0.20 & 0.30).
The RETEST family CANNOT break the micro-BOS frequency wall while holding the edge:

  * The retest-ladder mechanics (shallow / breaker-at-level / deep 2nd-chance) are
    INERT for frequency under the engine's one-position-at-a-time rule: the shallow
    limit always wins the fill race, so breaker/deep never fill (OOS N pinned at ~33
    whether 1 or 3 ladder levels are armed). Likewise the in-run re-arm (price-step
    OR bar-cadence) adds ~0 independent fills, because the open position blocks every
    re-arm and the break runs are shorter than the hold.
  * Replacing the trailing exit with a finite TP to cycle positions faster (the only
    way a ladder could yield independent fills) DESTROYS the edge: every finite-TP
    config fell to t25 PF 0.55-0.81. The trailing exit IS the edge.
  * Loosening the displacement/structure filter to raise the EVENT count collapses PF:
    K 1.8->1.2 or LOOKBACK 80->40 takes OOS N to ~110-150 but t25 PF to ~0.70-0.91.

  THE FRONTIER (OOS, NOBIAS, RETR_A 0.25, trail-only, K 1.8, LOOKBACK 80):
    - core London+NY hours (07-15 UTC) : N=33, t/d 1.06, PF 1.58/1.49/1.40 @20/25/30
      taker -> EDGE INTACT (clears PF>=1.3 @0.25 and positive @0.30), but ~1 trade/day.
    - wide hours (06-20 UTC)           : N=112, t/d 1.20, PF 1.22/1.14/1.06 @20/25/30
      taker -> clears OOS-N>=100 and stays POSITIVE at 0.30, but PF<1.3 @0.25 (FAIL).
  There is NO config with OOS N>=100 AND PF>=1.3 @0.25: max N at the PF gate is ~33.
  This reproduces the wall hit by all 10 prior micro-BOS frequency attempts (best prior
  ~1.37 trades/day). COMMITTED DEFAULT = the PF-passing frontier endpoint (core hours);
  removing the slow-EMA bias gate and using a 0.25-disp retest STRENGTHENS the surviving
  edge (t25 PF 1.22 base -> 1.49) at the same ~1 trade/day. Not a round-2 pass; the
  frequency<->edge frontier is the evidence-backed deliverable. Set MB_HRS=1 to see the
  N=112 endpoint.

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only (info up to bar i close).
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_retest_family"


def _f(name, d):
    return float(os.environ.get(name, d))


def _i(name, d):
    return int(os.environ.get(name, d))


# --- tunable params (env-overridable for the sweep) ---
LOOKBACK   = _i("MB_LOOKBACK", 80)      # S5 bars defining the micro-structure extreme
K_DISP     = _f("MB_K", 1.8)            # displacement: close beyond extreme >= K*M1-ATR
RETR_A     = _f("MB_RA", 0.25)          # shallow retest depth (fraction of disp)
RETR_C     = _f("MB_RC", 0.70)          # deep 2nd-chance retest depth
USE_BREAKER = _i("MB_BREAKER", 0)       # include limit at the broken level itself (inert under 1-pos)
USE_DEEP    = _i("MB_DEEP", 0)          # include the deep 2nd-chance limit (inert under 1-pos)
REARM_STEP = _f("MB_REARM", 0.60)       # re-arm when leg advances >= step*ATR (0=off->edge only)
SL_PTS     = _f("MB_SL", 5.0)           # structure-wide stop from fill
TTL        = _i("MB_TTL", 90)           # bars a retest limit stays live
ATR_LO     = _f("MB_ATRLO", 0.20)       # skip dead tape
ATR_HI     = _f("MB_ATRHI", 1.60)       # skip runaway tape
BIAS_EMA   = _i("MB_BIAS", 3600)        # slow S5 EMA for trend bias
COOLDOWN   = _i("MB_COOL", 12)          # bars after a close before next entry
MAXHOLD    = _i("MB_MAXHOLD", 600)      # time stop (bars)
TRAIL      = _f("MB_TRAIL", 4.0)        # trailing stop distance
TP_PTS     = _f("MB_TP", 0.0)           # finite take-profit pts (0 -> trail-only/inf)
REARM_BARS = _i("MB_REARM_BARS", 0)     # re-emit retest every N bars within a break run (0=off)

_HRS = {0: (7, 8, 9, 10, 11, 12, 13, 14, 15),                 # London+NY active (default)
        1: tuple(range(6, 21)),                                # wide 06-20 UTC
        2: (8, 9, 10, 11, 12, 13, 14, 15, 16, 17)}             # London open -> NY pm
SESSION_HOURS = _HRS[_i("MB_HRS", 0)]

SIM = dict(maxhold=MAXHOLD, dollars_per_point=1.0, commission=0.07, cooldown=COOLDOWN,
           trail_pts=TRAIL, be_at_pts=0.0)


def _m1_atr_aligned(b: Bars):
    """Wilder ATR on M1 mid bars, aligned to S5 by the LAST COMPLETED M1 bar (causal)."""
    r = resample(b, 60)
    h, l, c = r["h"], r["l"], r["c"]
    pc = np.empty_like(c); pc[0] = c[0]; pc[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    a = 1.0 / 14.0
    out = np.empty_like(tr); out[0] = tr[0]
    for i in range(1, len(tr)):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
    s5idx = r["s5_idx"]
    pos = np.searchsorted(s5idx, np.arange(b.n), side="right") - 1
    al = np.full(b.n, np.nan)
    ok = pos >= 0
    al[ok] = out[pos[ok]]
    return al


def generate(b: Bars) -> Signals:
    mid = b.mid
    A1 = _m1_atr_aligned(b)
    Eb = ema(mid, BIAS_EMA)
    rmax = roll_max(mid, LOOKBACK)
    rmin = roll_min(mid, LOOKBACK)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    if _i("MB_NOBIAS", 1):
        bias_up = np.ones(b.n, bool); bias_dn = np.ones(b.n, bool)
    else:
        bias_up = mid > Eb
        bias_dn = mid < Eb

    disp_up = mid - rmax          # >0 when broken above prior extreme
    disp_dn = rmin - mid          # >0 when broken below prior extreme
    thr = K_DISP * A1

    brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
    brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn

    iu = _armed(brk_up, mid, A1, +1)
    il = _armed(brk_dn, mid, A1, -1)

    # build ladder of maker limits for each armed event
    ev_i = []; ev_side = []; ev_level = []
    for idx in iu:
        d = disp_up[idx]
        broken = rmax[idx]                      # the structure level that was broken
        ev_i.append(idx); ev_side.append(+1); ev_level.append(mid[idx] - RETR_A * d)
        if USE_BREAKER:
            ev_i.append(idx); ev_side.append(+1); ev_level.append(broken)
        if USE_DEEP:
            ev_i.append(idx); ev_side.append(+1); ev_level.append(mid[idx] - RETR_C * d)
    for idx in il:
        d = disp_dn[idx]
        broken = rmin[idx]
        ev_i.append(idx); ev_side.append(-1); ev_level.append(mid[idx] + RETR_A * d)
        if USE_BREAKER:
            ev_i.append(idx); ev_side.append(-1); ev_level.append(broken)
        if USE_DEEP:
            ev_i.append(idx); ev_side.append(-1); ev_level.append(mid[idx] + RETR_C * d)

    if not ev_i:
        return Signals(i=[], side=[], kind=[], level=[], sl_pts=[], tp_pts=[], ttl=[])

    i = np.asarray(ev_i, np.int64)
    side = np.asarray(ev_side, np.int64)
    level = np.asarray(ev_level, np.float64)
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(n, int),                # LIMIT maker entry at the retest
        level=level,
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, TP_PTS if TP_PTS > 0 else np.inf),
        ttl=np.full(n, TTL, np.int64),
    )


def _armed(brk, mid, A1, direction):
    """Return indices where a fresh break arms an order. With REARM_STEP>0, also
    re-arm as the leg advances by >= REARM_STEP*ATR beyond the last armed extreme
    (continuation ladder). Purely causal: each emit uses only mid[idx], A1[idx]."""
    idxs = np.where(brk)[0]
    if len(idxs) == 0:
        return idxs
    if REARM_STEP <= 0:
        # fresh rising edge only (one per contiguous break run)
        keep = np.ones(len(idxs), bool)
        keep[1:] = (np.diff(idxs) > 1)
        return idxs[keep]
    out = []
    last_px = None
    last_bar = -10**9
    prev = -10
    for idx in idxs:
        contiguous = (idx == prev + 1)
        prev = idx
        px = mid[idx]
        step = REARM_STEP * (A1[idx] if np.isfinite(A1[idx]) else 0.0)
        if last_px is None:
            out.append(idx); last_px = px; last_bar = idx
            continue
        if not contiguous:
            # new break run after a gap in the boolean -> always a fresh event
            out.append(idx); last_px = px; last_bar = idx
            continue
        # within a contiguous run: re-arm on leg advance OR on a fixed bar-cadence
        adv = (direction > 0 and px >= last_px + step) or \
              (direction < 0 and px <= last_px - step)
        cadence = REARM_BARS > 0 and (idx - last_bar) >= REARM_BARS
        if adv or cadence:
            out.append(idx); last_px = px; last_bar = idx
    return np.asarray(out, np.int64)
