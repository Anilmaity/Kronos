"""Micro-BOS continuation with INTRA-LEG RE-ARM (frequency lever on the proven base).

BASE (bot/micro/strat_r3_1.py == micro_bos_cont_maker): a displacement break of
micro-structure (mid beyond the last LOOKBACK-bar extreme by >= K*M1-ATR), trend-
and session-filtered, entered as a MAKER limit on a shallow retest, with a structure
stop + trailing exit. The base proved a REAL edge at realistic spread (OOS spread
grid: 0.20 taker PF 1.33, 0.30 taker PF 1.10) but fires only the ONE fresh break
edge per leg -> ~35 OOS trades (~1.1/day), below the >=100 / 3-25-per-day floor.

THE LEVER -- RE-ARM WITHIN A LEG. The narrow `disp >= K*ATR` window is just the
spike (roll_max catches up in ~7 min), so the base's "one signal per break" leaves
the whole continuation untraded. Here a LEG is opened by a quality displacement break
and then PERSISTS while the EMA bias holds, the session is active, and price has not
structurally retraced (mid above leg_high - LEG_INVALID). Throughout the live leg we
re-arm a fresh continuation maker-limit on:
  (a) each further EXTENSION (a new leg-high, long case), and
  (b) each fresh HIGHER-LOW (a pullback low holding above the prior pullback low that
      then bounces), with a per-leg RE-ARM cooldown so rungs don't cluster.
Each rung is a maker limit a hair below price (RETR_K * M1-ATR), so it only fills on a
real micro-pullback -- a continuation entry on a dip, not a chase. A tighter trailing
exit lets a position exit on each minor pullback so the next higher-low rung can take
the resumption: one trade per continuation WAVE instead of one per whole leg.

Causal: a forward loop using info up to bar i close only (same discipline as ema()).
M1-ATR aligned to the last completed M1 bar; roll_max/min causal; no future indexing.

HONEST RESULT (the deliverable, not a pass). Official runner, OOS 2025-08..2026-06,
judged on oos_spread_grid taker PF. The re-arm lever IS a real frequency lever, but it
trades against the edge monotonically -- the micro-BOS edge is a property of the FIRST
displacement break's shallow retest and does NOT generalise to re-entries in the leg:

  config (env)                         OOS trades   0.20 tak   0.30 tak   ~0.25 tak
  BASE strat_r3_1 (1 signal / leg)        35          1.33       1.10       ~1.21
  STRICT ext-rungs (MB_STRICT1 HL0)       34          0.986      0.792      ~0.89
  C broad-leg+HL K1.8  (DEFAULT)          61          0.945      0.910      ~0.93
  D broad+HL K1.35 (MB_K1.35 GAP10)      127          0.637      0.565      ~0.60
  E broad+HL LB60 K1.3 (MB_LB60 K1.3)    154          0.664      0.592      ~0.63

Findings: (1) even a strict, displacement-gated re-arm at the SAME ~34 trades drops the
0.20-taker PF from the base's 1.33 to 0.99 -- every extra rung is a negative-edge trade.
(2) Reaching the >=100-trade floor (D, E) collapses ~0.25-taker PF to ~0.60 and turns net
deeply negative (-$90..-$120). (3) frequency is double-capped: signal quality falls with
loosening, AND the trailing ride keeps one position per wave so trades/day only reaches
~1.9 even at 154 OOS trades -- shorter fixed-TP exits raise turnover but kill PF further
(tested: trail2/TP-fixed -> 0.20-taker PF ~1.03). The PF>=1.3 @0.25-taker AND >=100-trade
constraint is INFEASIBLE for this family; the edge tops out at the base's ~35 trades
(~1.1/day, ~0.25-taker PF ~1.2). Config C (default) is the Pareto-best re-arm compromise
-- ~2x the base frequency -- but still fails the bar (0.25-taker PF ~0.93). Reported for
the evidence; not deployable as a taker. This confirms scout finding #5 (frequency<->edge
inverse on XAU 5s) and the r3_1 refutation from the high-frequency side.

CONTRACT: generate(b)->Signals ; SIM ; NAME.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_rearm"


def _f(k, d):
    return float(os.environ.get(k, d))


def _i(k, d):
    return int(os.environ.get(k, d))


# SIM aligned to the proven base (strat_r3_1): trail-ride, structure stop, cooldown.
SIM = dict(maxhold=_i("MB_MAXHOLD", 600), dollars_per_point=1.0, commission=0.07,
           cooldown=_i("MB_COOLDOWN", 12), trail_pts=_f("MB_TRAIL", 4.0), be_at_pts=0.0)

# --- base micro-BOS params (proven r3_1 values are the defaults) ---
LOOKBACK = _i("MB_LB", 80)        # S5 bars defining the micro-structure extreme
K_DISP   = _f("MB_K", 1.8)        # displacement: close beyond extreme by >= K_DISP * M1-ATR
RETR     = _f("MB_RETR", 0.30)    # retest depth as a fraction of the displacement
SL_PTS   = _f("MB_SL", 5.0)       # structure-wide stop from fill
TP_PTS   = np.inf                 # trail-only exit (SIM.trail_pts rides the wave)
TTL      = _i("MB_TTL", 90)       # bars the retest limit stays live
ATR_LO   = 0.20
ATR_HI   = 1.60
BIAS_EMA = 3600
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY active (UTC)

# --- re-arm lever params (defaults = config C, the Pareto-best re-arm point) ---
STRICT      = _i("MB_STRICT", 0)  # 1 = re-arm only while displacement (brk) still holds
HL_ON       = _i("MB_HL", 1)      # 1 = also re-arm on fresh higher-lows
LEG_INVALID = _f("MB_INV", 6.0)   # leg dies if mid retraces this many pts off the extreme
REARM_GAP   = _i("MB_GAP", 14)    # min bars between re-arms within one leg
EXT_PTS     = _f("MB_EXT", 0.40)  # extension rung needs a new extreme this many pts beyond prior
PB_PTS      = _f("MB_PB", 0.50)   # higher-low needs this much pullback then bounce
RETR_K      = _f("MB_RETRK", 0.30)  # fallback retest depth (xM1-ATR) when disp<=0
MAX_RUNGS   = _i("MB_MR", 30)


def _m1_atr_aligned(b: Bars):
    """Wilder ATR on M1 mid bars, aligned to S5 by the LAST COMPLETED M1 bar
    (causal). Returns array length b.n (nan before the first M1 completes)."""
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
    bias_up = mid > Eb
    bias_dn = mid < Eb

    disp_up = mid - rmax          # >0 when broken above
    disp_dn = rmin - mid          # >0 when broken below
    thr = K_DISP * A1

    brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
    brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn

    n = b.n
    a1 = np.where(np.isfinite(A1), A1, 0.0)
    sig_i = []; sig_side = []; sig_level = []

    def lvl_long(i, m):
        return m - (RETR * disp_up[i] if disp_up[i] > 0 else RETR_K * a1[i])

    def lvl_short(i, m):
        return m + (RETR * disp_dn[i] if disp_dn[i] > 0 else RETR_K * a1[i])

    # ---------------- LONG legs ----------------
    leg = False
    leg_high = -np.inf; rung_high = -np.inf; pb_low = np.inf; prev_hl = -np.inf
    last_emit = -10**9; rungs = 0
    for i in range(n):
        if not leg:
            if brk_up[i]:
                leg = True
                sig_i.append(i); sig_side.append(1); sig_level.append(lvl_long(i, mid[i]))
                last_emit = i; leg_high = mid[i]; rung_high = mid[i]
                pb_low = mid[i]; prev_hl = -np.inf; rungs = 1
            continue
        m = mid[i]
        # leg invalidation: bias flip, session end, or structural retrace
        if (not bias_up[i]) or (not sess[i]) or (m < leg_high - LEG_INVALID):
            leg = False
            continue
        # STRICT: rungs only while displacement still holds (genuine momentum)
        if STRICT and not brk_up[i]:
            if m > leg_high:
                leg_high = m; pb_low = m
            elif m < pb_low:
                pb_low = m
            continue
        if m > leg_high:
            leg_high = m
            # extension rung
            if (m - rung_high) >= EXT_PTS and (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS:
                sig_i.append(i); sig_side.append(1); sig_level.append(lvl_long(i, m))
                last_emit = i; rung_high = m; rungs += 1
            pb_low = m
        else:
            if m < pb_low:
                pb_low = m
            # fresh higher-low: pullback held above prior HL, then bounced PB_PTS off pb_low
            if HL_ON and (pb_low > prev_hl) and ((leg_high - pb_low) >= PB_PTS) and ((m - pb_low) >= PB_PTS) \
               and (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS:
                sig_i.append(i); sig_side.append(1); sig_level.append(lvl_long(i, m))
                last_emit = i; prev_hl = pb_low; rungs += 1; pb_low = m

    # ---------------- SHORT legs (mirror) ----------------
    leg = False
    leg_low = np.inf; rung_low = np.inf; pb_high = -np.inf; prev_lh = np.inf
    last_emit = -10**9; rungs = 0
    for i in range(n):
        if not leg:
            if brk_dn[i]:
                leg = True
                sig_i.append(i); sig_side.append(-1); sig_level.append(lvl_short(i, mid[i]))
                last_emit = i; leg_low = mid[i]; rung_low = mid[i]
                pb_high = mid[i]; prev_lh = np.inf; rungs = 1
            continue
        m = mid[i]
        if (not bias_dn[i]) or (not sess[i]) or (m > leg_low + LEG_INVALID):
            leg = False
            continue
        if STRICT and not brk_dn[i]:
            if m < leg_low:
                leg_low = m; pb_high = m
            elif m > pb_high:
                pb_high = m
            continue
        if m < leg_low:
            leg_low = m
            if (rung_low - m) >= EXT_PTS and (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS:
                sig_i.append(i); sig_side.append(-1); sig_level.append(lvl_short(i, m))
                last_emit = i; rung_low = m; rungs += 1
            pb_high = m
        else:
            if m > pb_high:
                pb_high = m
            if HL_ON and (pb_high < prev_lh) and ((pb_high - leg_low) >= PB_PTS) and ((pb_high - m) >= PB_PTS) \
               and (i - last_emit) >= REARM_GAP and rungs < MAX_RUNGS:
                sig_i.append(i); sig_side.append(-1); sig_level.append(lvl_short(i, m))
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
        kind=np.ones(m, int),                # LIMIT maker entry at the retest
        level=level,
        sl_pts=np.full(m, SL_PTS),
        tp_pts=np.full(m, TP_PTS),
        ttl=np.full(m, TTL, np.int64),
    )
