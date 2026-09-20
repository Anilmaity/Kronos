"""EDGE_microbos -- the deployable micro-BOS continuation survivor (Round 2).

WHAT THIS IS
------------
The single best taker-survivable candidate from the micro-BOS frequency-expansion
search. It is the MULTISCALE + INTRA-LEG RE-ARM continuation: deep maker-limit
retests of fresh micro-displacement breaks (close beyond a prior-N S5 extreme by
>= K*M1-ATR), trend-aligned (slow S5 EMA) and session-gated (London + NY-morning,
07-15 UTC), held with a structure-wide stop + chandelier trail so a real
continuation leg can run. Openers fire at four S5 lookbacks and each persistent
leg re-arms extra entries as the single-position engine frees.

VERIFIED EDGE (real OANDA S5 ticks; train 2024-01..2025-07, OOS 2025-08..2026-06;
judged on runner oos_spread_grid, taker = cross the constant spread):
  OOS grid N = 138 (~1.5 trades/day)
  0.20 taker : PF 1.54 , net +$111 , WR 44.9%
  0.30 taker : PF 1.28 , net +$64
  => ~1.41 PF at 0.25 taker, clearly positive at 0.30 taker. maxDD ~ $107 / $5k.
  Passes Round-2 bar: OOS>=100, PF>=1.3 @0.25 taker, positive @0.30 taker, no look-ahead.

REQUIRED LIVE SPREAD (the load-bearing deploy caveat)
-----------------------------------------------------
This edge ONLY exists if the live XAU feed delivers <= ~0.25pt spread in 07-15 UTC.
  * Break-even live spread is ~0.30-0.33 taker (PF still > 1 at 0.30; the 1.5x-cost
    stress pass at the wide 0.66 OANDA-practice feed is NET NEGATIVE).
  * TRAIN-window spread-grid PF is < 1: the realistic-spread taker edge is a property
    of the 2025-26 OOS regime, not an all-history plateau. Treat as fragile.
  * The funded account (FundingPips MT5, acct 6c7ce166) is MARKET-EXECUTION / taker
    only. Before risking it, MEASURE the actual XAU spread in 07-15 UTC. If it sits
    above ~0.30, this is NOT deployable there and the H4 trend-follow
    (bot/challenge_xau.py) remains the deployable path.

FREQUENCY CEILING (the honest finding, do not paper over)
---------------------------------------------------------
~1.5 trades/day is a HARD ceiling, not a tuning artifact. generate() emits ~668 raw
OOS signals (~7.4/day) but ~80% are skipped by single-position occupancy: they are
COINCIDENT breaks of the SAME trend leg across the four scales + rungs. Distinct
continuation legs in London/NY occur only ~1.5/day on XAU 5s. Levers that try to
lift throughput were all measured (TTL, maxhold, trail, cooldown, rung-gates,
scale-count) and NONE breaks ~1.5/day with the edge intact -- shortening the hold or
trail lifts N a little but collapses PF (the trailed runner IS the edge); loosening
K/RETR drives PF straight through 1.0 (they ARE the edge). The user's 5-20/day goal
is therefore NOT jointly reachable with a real edge on this signal/timeframe; ~1-1.5
trades/day is the true ceiling. Reported as the deliverable, not hidden.

ROBUSTNESS: PF@0.25 taker stays in a 1.40-1.52 block across cooldown 0/6, rung-gap
6-18, max-rungs 24-80, ext 0.3-0.7, and 3-8 scale unions (N 133-152 throughout) --
a genuine plateau on the frequency axes. The cliffs are confined to K_DISP (~1.8
threshold) and RETR (~0.62 peak), which are the edge itself.

NO LOOK-AHEAD: roll_max/min causal (prev-w window, excludes current bar) at all
scales; M1-ATR aligned to the LAST COMPLETED M1 bar; EMA past-only; every signal is
a limit acted on the bar AFTER its decision bar and filled next-bar by the engine;
the leg re-arm loop reads info only up to bar i close. Absolute imports.

CONTRACT: generate(b)->Signals ; SIM ; NAME.  Source: strat_mb_r3_4.py, proven config.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "EDGE_microbos"


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


SIM = dict(maxhold=_P("MB_MAXHOLD", 600, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("MB_COOLDOWN", 6, int), trail_pts=_P("MB_TRAIL", 4.0),
           be_at_pts=0.0)

# --- multiscale opener lookbacks (the first frequency lever) ---
LOOKBACKS = tuple(int(x) for x in os.environ.get("MB_LBS", "48,72,112,176").split(","))
# --- the lookback whose legs carry the re-arm rungs (primary structure) ---
LEG_LB   = _P("MB_LEGLB", 96, int)

# --- shared micro-BOS params (cont_sym broadened winning config) ---
K_DISP   = _P("MB_K", 1.80)               # displacement floor >= K_DISP * M1-ATR
RETR     = _P("MB_RETR", 0.62)            # retest depth (deep) -- good maker fill
SL_PTS   = _P("MB_SL", 5.0)               # structure-wide stop from fill
TP_PTS   = np.inf                          # trail-only exit (SIM.trail_pts rides the leg)
TTL      = _P("MB_TTL", 480, int)         # retest limit live bars (~40 min)
ATR_LO   = _P("MB_ATRLO", 0.18)
ATR_HI   = _P("MB_ATRHI", 8.0)            # admit volatile breaks -> both-sides symmetry
BIAS_EMA = _P("MB_BIAS", 3600, int)       # slow S5 EMA trend bias (~5h)
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("MB_HOURS", "7,8,9,10,11,12,13,14,15").split(","))

# --- re-arm lever params ---
REARM_ON   = _P("MB_REARM", 1, int)
EXT_ON     = _P("MB_EXT_ON", 1, int)      # extension rung
HL_ON      = _P("MB_HL", 1, int)          # displacement-gated higher-low rung
LEG_INVALID = _P("MB_INV", 6.0)           # leg dies if price retraces this many pts off extreme
REARM_GAP  = _P("MB_GAP", 18, int)        # min bars between rungs within one leg
EXT_PTS    = _P("MB_EXT", 0.70)           # extension rung: new extreme >= this beyond prior rung
PB_PTS     = _P("MB_PB", 0.80)            # higher-low rung: pullback then bounce of this size
HL_LB      = _P("MB_HLLB", 24, int)       # short lookback for the HL bounce displacement gate
HL_K       = _P("MB_HLK", 0.90)           # HL bounce must displace >= HL_K * M1-ATR
RETR_FLOOR = _P("MB_RFLOOR", 0.40)
MIN_DEPTH  = _P("MB_MINDEPTH", 0.50)      # rung limit must sit >= this many pts inside (maker)
MAX_RUNGS  = _P("MB_MR", 24, int)


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


def _scale_breaks(mid, A1, sess, volok, bias_up, bias_dn, lookback):
    """Fresh micro-BOS break edges + their displacement for one lookback."""
    rmax = roll_max(mid, lookback)
    rmin = roll_min(mid, lookback)
    disp_up = mid - rmax
    disp_dn = rmin - mid
    thr = K_DISP * A1
    brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
    brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn
    fu = brk_up.copy(); fu[1:] &= ~brk_up[:-1]
    fd = brk_dn.copy(); fd[1:] &= ~brk_dn[:-1]
    return fu, fd, disp_up, disp_dn


def generate(b: Bars) -> Signals:
    mid = b.mid
    n = b.n
    A1 = _m1_atr_aligned(b)
    a1 = np.where(np.isfinite(A1), A1, 0.0)
    Eb = ema(mid, BIAS_EMA)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    bias_up = mid > Eb
    bias_dn = mid < Eb

    sig_i = []; sig_side = []; sig_level = []

    # ---------------- (A) MULTISCALE OPENERS ----------------
    # union of fresh breaks across lookbacks; each a deep maker limit at its own
    # displacement. The engine serialises coincident ones by occupancy.
    for lb in LOOKBACKS:
        fu, fd, dup, ddn = _scale_breaks(mid, A1, sess, volok, bias_up, bias_dn, lb)
        for i in np.where(fu)[0]:
            sig_i.append(int(i)); sig_side.append(1)
            sig_level.append(mid[i] - RETR * dup[i])
        for i in np.where(fd)[0]:
            sig_i.append(int(i)); sig_side.append(-1)
            sig_level.append(mid[i] + RETR * ddn[i])

    # ---------------- (B) INTRA-LEG RE-ARM on the primary lookback ----------------
    if REARM_ON:
        fu, fd, disp_up, disp_dn = _scale_breaks(mid, A1, sess, volok, bias_up, bias_dn, LEG_LB)
        # short-lookback extremes for the displacement-gated higher-low rung
        smax = roll_max(mid, HL_LB)
        smin = roll_min(mid, HL_LB)

        # LONG legs
        leg = False
        leg_high = -np.inf; rung_high = -np.inf; pb_low = np.inf; prev_hl = -np.inf
        last_emit = -10**9; rungs = 0
        for i in range(n):
            if not leg:
                if fu[i]:
                    leg = True
                    leg_high = mid[i]; rung_high = mid[i]
                    pb_low = mid[i]; prev_hl = -np.inf; rungs = 1; last_emit = i
                continue
            m = mid[i]
            if (not bias_up[i]) or (not sess[i]) or (m < leg_high - LEG_INVALID):
                leg = False
                continue
            gap_ok = (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS
            if m > leg_high:
                leg_high = m
                # (1) EXTENSION rung
                if EXT_ON and (m - rung_high) >= EXT_PTS and gap_ok:
                    D = disp_up[i] if disp_up[i] > RETR_FLOOR * a1[i] else max(m - pb_low, RETR_FLOOR * a1[i])
                    if RETR * D >= MIN_DEPTH:
                        sig_i.append(i); sig_side.append(1)
                        sig_level.append(m - RETR * D)
                        last_emit = i; rung_high = m; rungs += 1
                pb_low = m
            else:
                if m < pb_low:
                    pb_low = m
                # (2) DISPLACEMENT-GATED HIGHER-LOW rung: pullback held above the
                # prior HL, then the bounce itself breaks the short-lookback high by
                # >= HL_K*ATR (a fresh micro-BOS in-trend, not a bare dip-buy).
                if HL_ON and gap_ok and (pb_low > prev_hl) and ((leg_high - pb_low) >= PB_PTS) \
                   and np.isfinite(smax[i]) and (m - smax[i] >= HL_K * a1[i]):
                    D = max(m - pb_low, RETR_FLOOR * a1[i])
                    if RETR * D >= MIN_DEPTH:
                        sig_i.append(i); sig_side.append(1)
                        sig_level.append(m - RETR * D)
                        last_emit = i; prev_hl = pb_low; rungs += 1; pb_low = m

        # SHORT legs (mirror)
        leg = False
        leg_low = np.inf; rung_low = np.inf; pb_high = -np.inf; prev_lh = np.inf
        last_emit = -10**9; rungs = 0
        for i in range(n):
            if not leg:
                if fd[i]:
                    leg = True
                    leg_low = mid[i]; rung_low = mid[i]
                    pb_high = mid[i]; prev_lh = np.inf; rungs = 1; last_emit = i
                continue
            m = mid[i]
            if (not bias_dn[i]) or (not sess[i]) or (m > leg_low + LEG_INVALID):
                leg = False
                continue
            gap_ok = (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS
            if m < leg_low:
                leg_low = m
                if EXT_ON and (rung_low - m) >= EXT_PTS and gap_ok:
                    D = disp_dn[i] if disp_dn[i] > RETR_FLOOR * a1[i] else max(pb_high - m, RETR_FLOOR * a1[i])
                    if RETR * D >= MIN_DEPTH:
                        sig_i.append(i); sig_side.append(-1)
                        sig_level.append(m + RETR * D)
                        last_emit = i; rung_low = m; rungs += 1
                pb_high = m
            else:
                if m > pb_high:
                    pb_high = m
                if HL_ON and gap_ok and (pb_high < prev_lh) and ((pb_high - leg_low) >= PB_PTS) \
                   and np.isfinite(smin[i]) and (smin[i] - m >= HL_K * a1[i]):
                    D = max(pb_high - m, RETR_FLOOR * a1[i])
                    if RETR * D >= MIN_DEPTH:
                        sig_i.append(i); sig_side.append(-1)
                        sig_level.append(m + RETR * D)
                        last_emit = i; prev_lh = pb_high; rungs += 1; pb_high = m

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
        kind=np.ones(m, int),
        level=level,
        sl_pts=np.full(m, SL_PTS),
        tp_pts=np.full(m, TP_PTS),
        ttl=np.full(m, TTL, np.int64),
    )
