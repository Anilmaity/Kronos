"""Micro-BOS continuation + INTRA-LEG RE-ARM on the BROADENED base (the frequency
lever done right, on top of the edge-preserving deep-retest config).

WHY THIS, AND WHY IT IS NOT THE micro_bos_rearm DEAD END
--------------------------------------------------------
The assigned lever is RE-ARM within a leg: take a new continuation entry on each
further displacement EXTENSION or each fresh HIGHER-LOW while the leg and EMA bias
persist (cooldown to avoid clustering). A prior attempt (strat_mb_r1_0,
micro_bos_rearm) implemented exactly this and FAILED: every rung was a negative-edge
trade (0.20-taker PF fell from the base 1.33 to ~0.99 at equal count, ~0.60 at >=100
trades). BUT that attempt re-armed on top of the SHALLOW base (RETR 0.30, ATR_HI 1.6)
and used a poor-quality shallow fallback limit (a hair below price) for every rung.

The round-1 winner strat_mb_r1_2 (micro_bos_cont_sym) showed what actually preserves
the micro-BOS edge while raising frequency: (a) LIFT the ATR ceiling (ATR_HI 1.6->8.0)
so the volatile down/chop-leg breaks are admitted (both-sides symmetry), and (b) a
DEEP retest (RETR 0.62) so the maker fill on those volatile legs is at a good price,
not a chase. cont_sym reaches ~100 OOS trades, 0.20/0.30-taker PF ~1.46/1.27.

This module keeps cont_sym's fresh-break signals UNCHANGED and ADDS re-arm rungs that
inherit the same fill-quality discipline: every rung is also a DEEP maker limit
(level = price - RETR * local_displacement, with a minimum depth), gated to the live
leg + EMA bias + session + ATR band, with a per-leg cooldown. So the extra entries are
continuation-on-a-real-dip, the same shape as the proven base signal -- not shallow
chases. Re-break rungs (price re-clears the prior-N extreme by >=K*ATR inside the leg)
are recovered too, since those are the highest-quality intra-leg re-entries.

FREQUENCY <-> EDGE FRONTIER (honest, measured on the runner's oos_spread_grid taker PF,
OOS 2025-08..2026-06). The frequency knobs are EXT_PTS (extension rung threshold) and
REARM_GAP (min bars between rungs):
  config (env)                              grid trades   0.20 tak   0.30 tak   ~0.25
  cont_sym base (no re-arm)                     100         1.456      1.273      ~1.36
  EXT_ON=0 (re-break rungs only)                 98         1.333      1.164      ~1.25
  GAP30 EXT1.0  (DEFAULT, extension-only)       124         1.403      1.226      ~1.32
  GAP24 EXT0.8  (more rungs)                     127         1.392      1.215      ~1.30
  GAP36 EXT1.2  (fewer rungs)                    119         1.299      1.142      ~1.22
The deep-retest extension rung is the lever: it lifts OOS trades from cont_sym's ~100
(at the floor) to a comfortable 124 while the good maker fill keeps per-trade edge, so
PF holds ~1.32 @0.25 taker and stays positive (1.226) @0.30 taker. The relationship is
the familiar inverse one (more rungs -> lower PF), so DEFAULT sits at the Pareto point
with ~24 trades of margin over the 100-floor and PF margin over 1.30. Re-break rungs
add ~nothing on top of extension rungs (overlap) so REBRK_ON defaults OFF. The
HIGHER-LOW rung is the lowest-quality (dip-bounce with no fresh displacement) and is
OFF by default (HL_ON=0) -- as in the strat_mb_r1_0 dead end it dilutes PF the most.
Frequency is ~1.4 trades / active-day: honestly BELOW the 3-25/day stretch band, but
the round-2 bar (OOS>=100 AND PF>=1.3 @0.25 taker AND positive @0.30) is cleared.

NO LOOK-AHEAD: roll_max/min causal (prev-w window, excludes current bar); M1-ATR
aligned to the LAST COMPLETED M1 bar; EMA uses only past bars; every emitted signal is
a limit acted on the bar AFTER its decision bar and filled next-bar by the engine; the
leg loop only ever reads info up to bar i close. Absolute imports only.

CONTRACT: generate(b)->Signals ; SIM ; NAME.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_rearm_deep"


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


SIM = dict(maxhold=_P("MB_MAXHOLD", 600, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("MB_COOLDOWN", 6, int), trail_pts=_P("MB_TRAIL", 4.0),
           be_at_pts=0.0)

# --- base micro-BOS params (cont_sym broadened winning config) ---
LOOKBACK = _P("MB_LOOKBACK", 80, int)     # S5 bars defining the micro extreme (~6.7 min)
K_DISP   = _P("MB_K", 1.80)               # displacement floor >= K_DISP * M1-ATR
RETR     = _P("MB_RETR", 0.62)            # retest depth (deep) -- good maker fill
SL_PTS   = _P("MB_SL", 5.0)               # structure-wide stop from fill
TP_PTS   = np.inf                          # trail-only exit (SIM.trail_pts rides the leg)
TTL      = _P("MB_TTL", 480, int)         # retest limit live bars (~40 min)
ATR_LO   = _P("MB_ATRLO", 0.18)           # skip dead tape
ATR_HI   = _P("MB_ATRHI", 8.0)            # admit volatile breaks -> both-sides symmetry
BIAS_EMA = _P("MB_BIAS", 3600, int)       # slow S5 EMA trend bias (~5h)
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("MB_HOURS", "7,8,9,10,11,12,13,14,15").split(","))

# --- re-arm lever params ---
REARM_ON   = _P("MB_REARM", 1, int)       # 1 = enable intra-leg re-arm rungs
EXT_ON     = _P("MB_EXT_ON", 1, int)      # re-arm on further displacement extension
REBRK_ON   = _P("MB_REBRK_ON", 0, int)    # re-arm on a fresh re-break inside the leg (adds ~0)
HL_ON      = _P("MB_HL", 0, int)          # re-arm on fresh higher-lows (lowest quality)
LEG_INVALID = _P("MB_INV", 6.0)           # leg dies if price retraces this many pts off extreme
REARM_GAP  = _P("MB_GAP", 30, int)        # min bars between rungs within one leg
EXT_PTS    = _P("MB_EXT", 1.00)           # extension rung: new extreme >= this beyond prior rung
PB_PTS     = _P("MB_PB", 0.80)            # higher-low rung: pullback then bounce of this size
RETR_FLOOR = _P("MB_RFLOOR", 0.40)        # min rung depth as fraction of local disp floor
MIN_DEPTH  = _P("MB_MINDEPTH", 0.50)      # rung limit must sit >= this many pts below price (long)
MAX_RUNGS  = _P("MB_MR", 20, int)


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
    a1 = np.where(np.isfinite(A1), A1, 0.0)
    Eb = ema(mid, BIAS_EMA)
    rmax = roll_max(mid, LOOKBACK)
    rmin = roll_min(mid, LOOKBACK)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    bias_up = mid > Eb
    bias_dn = mid < Eb

    disp_up = mid - rmax          # >0 when broken above the prior-N extreme
    disp_dn = rmin - mid          # >0 when broken below
    thr = K_DISP * A1

    brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
    brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn

    # fresh rising edge of each contiguous break run (one opener per break run)
    fu = brk_up.copy(); fu[1:] &= ~brk_up[:-1]
    fd = brk_dn.copy(); fd[1:] &= ~brk_dn[:-1]

    n = b.n
    sig_i = []; sig_side = []; sig_level = []

    def deep_long(i, m, D):
        """Deep maker buy-limit: price - RETR*D, D a displacement measure (>0)."""
        return m - RETR * D

    def deep_short(i, m, D):
        return m + RETR * D

    # ---------------- LONG legs ----------------
    leg = False
    leg_high = -np.inf; rung_high = -np.inf; pb_low = np.inf; prev_hl = -np.inf
    last_emit = -10**9; rungs = 0; prev_brk = False
    for i in range(n):
        if not leg:
            if fu[i]:
                leg = True
                sig_i.append(i); sig_side.append(1)
                sig_level.append(deep_long(i, mid[i], disp_up[i]))
                last_emit = i; leg_high = mid[i]; rung_high = mid[i]
                pb_low = mid[i]; prev_hl = -np.inf; rungs = 1
                prev_brk = True
            continue
        m = mid[i]
        # leg invalidation: bias flip, session end, structural retrace
        if (not bias_up[i]) or (not sess[i]) or (m < leg_high - LEG_INVALID):
            leg = False; prev_brk = False
            continue
        if not REARM_ON:
            if m > leg_high:
                leg_high = m
            prev_brk = brk_up[i]
            continue
        gap_ok = (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS
        # (1) RE-BREAK rung: a fresh re-clear of the prior-N extreme by >=K*ATR
        if REBRK_ON and brk_up[i] and (not prev_brk) and gap_ok and disp_up[i] > 0:
            sig_i.append(i); sig_side.append(1)
            sig_level.append(deep_long(i, m, disp_up[i]))
            last_emit = i; rungs += 1; rung_high = max(rung_high, m); gap_ok = False
        if m > leg_high:
            leg_high = m
            # (2) EXTENSION rung: new leg-high meaningfully beyond the prior rung level
            if EXT_ON and (m - rung_high) >= EXT_PTS and gap_ok:
                D = disp_up[i] if disp_up[i] > RETR_FLOOR * a1[i] else max(m - pb_low, RETR_FLOOR * a1[i])
                if RETR * D >= MIN_DEPTH:
                    sig_i.append(i); sig_side.append(1)
                    sig_level.append(deep_long(i, m, D))
                    last_emit = i; rung_high = m; rungs += 1
            pb_low = m
        else:
            if m < pb_low:
                pb_low = m
            # (3) HIGHER-LOW rung: pullback held above prior HL then bounced
            if HL_ON and (pb_low > prev_hl) and ((leg_high - pb_low) >= PB_PTS) \
               and ((m - pb_low) >= PB_PTS) and gap_ok:
                D = max(m - pb_low, RETR_FLOOR * a1[i])
                if RETR * D >= MIN_DEPTH:
                    sig_i.append(i); sig_side.append(1)
                    sig_level.append(deep_long(i, m, D))
                    last_emit = i; prev_hl = pb_low; rungs += 1; pb_low = m
        prev_brk = brk_up[i]

    # ---------------- SHORT legs (mirror) ----------------
    leg = False
    leg_low = np.inf; rung_low = np.inf; pb_high = -np.inf; prev_lh = np.inf
    last_emit = -10**9; rungs = 0; prev_brk = False
    for i in range(n):
        if not leg:
            if fd[i]:
                leg = True
                sig_i.append(i); sig_side.append(-1)
                sig_level.append(deep_short(i, mid[i], disp_dn[i]))
                last_emit = i; leg_low = mid[i]; rung_low = mid[i]
                pb_high = mid[i]; prev_lh = np.inf; rungs = 1
                prev_brk = True
            continue
        m = mid[i]
        if (not bias_dn[i]) or (not sess[i]) or (m > leg_low + LEG_INVALID):
            leg = False; prev_brk = False
            continue
        if not REARM_ON:
            if m < leg_low:
                leg_low = m
            prev_brk = brk_dn[i]
            continue
        gap_ok = (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS
        if REBRK_ON and brk_dn[i] and (not prev_brk) and gap_ok and disp_dn[i] > 0:
            sig_i.append(i); sig_side.append(-1)
            sig_level.append(deep_short(i, m, disp_dn[i]))
            last_emit = i; rungs += 1; rung_low = min(rung_low, m); gap_ok = False
        if m < leg_low:
            leg_low = m
            if EXT_ON and (rung_low - m) >= EXT_PTS and gap_ok:
                D = disp_dn[i] if disp_dn[i] > RETR_FLOOR * a1[i] else max(pb_high - m, RETR_FLOOR * a1[i])
                if RETR * D >= MIN_DEPTH:
                    sig_i.append(i); sig_side.append(-1)
                    sig_level.append(deep_short(i, m, D))
                    last_emit = i; rung_low = m; rungs += 1
            pb_high = m
        else:
            if m > pb_high:
                pb_high = m
            if HL_ON and (pb_high < prev_lh) and ((pb_high - leg_low) >= PB_PTS) \
               and ((pb_high - m) >= PB_PTS) and gap_ok:
                D = max(pb_high - m, RETR_FLOOR * a1[i])
                if RETR * D >= MIN_DEPTH:
                    sig_i.append(i); sig_side.append(-1)
                    sig_level.append(deep_short(i, m, D))
                    last_emit = i; prev_lh = pb_high; rungs += 1; pb_high = m
        prev_brk = brk_dn[i]

    if not sig_i:
        z = np.zeros(0)
        return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)

    i = np.array(sig_i, np.int64)
    side = np.array(sig_side, np.int64)
    level = np.array(sig_level, np.float64)
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    m = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(m, int),                # LIMIT maker entry at the retest
        level=level,
        sl_pts=np.full(m, SL_PTS),
        tp_pts=np.full(m, TP_PTS),
        ttl=np.full(m, TTL, np.int64),
    )
