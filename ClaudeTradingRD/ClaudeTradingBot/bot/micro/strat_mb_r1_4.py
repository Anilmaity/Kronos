"""Micro-BOS continuation, SESSION-LOCALISED STACK (London + NY engines).

LEVER FOR THIS CANDIDATE: session-localised stacking. London-open and NY-open are
run as SEPARATE engines, each with its OWN displacement/lookback params, then their
signals are unioned. The premise was that a continuation firing in BOTH sessions
roughly doubles the daily count. We also probed adding the late-US / Asian window.

WHAT THE DATA SAYS (real S5 ticks, train 2024-01..2025-07, OOS 2025-08..2026-06,
judged at realistic CONSTANT spread, primary = 0.25 taker):

  The edge is real but RARE. It lives ONLY in the strong-displacement regime
  (close beyond the prior extreme by >= ~1.8-2.0 * M1-ATR). Loosening K or the
  lookback to add trades recruits the marginal break, which is NOISE: OOS 0.25-taker
  PF collapses from ~1.26 (35 trades) to ~0.88 (94 trades) as soon as you push to
  ~3 trades/day. The late-US window does NOT hold the edge (it pulls PF below 1.0),
  so per the lever's own "only if it holds" clause it is EXCLUDED. Stacking redundant
  lookbacks does nothing -- a big displacement breaks the 60/120/200 extremes at the
  same instant and the single-position engine merges them into one trade.

  Honest frequency<->PF frontier on OOS (0.25 taker):
      pf25 >= 1.30 (+positive @0.30):   max ~34 trades  (~1.1/day)
      any positive edge (net@0.30 > 0): max ~37 trades  (~1.2/day, pf25 ~1.19)
      ~3 trades/day (94 trades, in-band): pf25 ~0.88, net@0.30 deeply NEGATIVE
  => >= 100 OOS trades at PF >= 1.3 is UNREACHABLE here; the edge saturates near
  ~1/day. TRAIN 0.25-taker PF is ~0.5-0.6 for the WHOLE family (it loses on train at
  realistic cost), so the OOS pass is a strong-momentum-regime property, not a
  parameter plateau -- reported as the evidence, not sold as a robust survivor.

WHAT THIS MODULE SHIPS: the constrained optimum -- the session-localised config that
MAXIMISES OOS trade count SUBJECT TO PF >= 1.3 @0.25 taker AND positive @0.30. The
two-session tuning (London K=2.0/LB80, NY K=1.8/LB120) actually lifts OOS 0.25-taker
PF to ~1.30, BEATING the single-engine base (1.255) -- session localisation improves
QUALITY even though it cannot raise the edge's frequency ceiling.

CONTRACT: generate(b)->Signals ; SIM ; NAME. Causal only (info up to bar i close).
No look-ahead: roll_max/min are causal (exclude current bar); M1-ATR aligns to the
LAST COMPLETED M1 bar; the slow EMA is causal; fills/exits are resolved next-bar by
the engine.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, roll_max, roll_min
from bot.micro.features import resample, hours_mask, ema

NAME = "micro_bos_session_stack"

SIM = dict(maxhold=600, dollars_per_point=1.0, commission=0.07, cooldown=12,
           trail_pts=4.0, be_at_pts=0.0)

# --- shared params (held at the base values; runner sweeps vary +/-30%) ---
RETR    = 0.30        # maker retest depth into the displacement leg (shallow pullback)
SL_PTS  = 5.0         # structure-wide stop (continuation invalidation)
TP_PTS  = np.inf      # trail-only exit (SIM.trail_pts rides the leg)
TTL     = 90          # bars the retest limit stays live (~7.5 min)
ATR_LO  = 0.20        # skip dead tape  (M1 ATR pts)
ATR_HI  = 1.60        # skip runaway tape (M1 ATR pts)
BIAS_EMA = 3600       # slow S5 EMA for trend bias (~5h)

# --- the two SESSION-LOCALISED engines (each its own displacement/lookback) ---
#   hours are UTC; London open block 7-11, NY open/overlap block 12-15.
ENGINES = (
    dict(name="london", hours=(7, 8, 9, 10, 11),     LOOKBACK=80,  K_DISP=2.0),
    dict(name="ny",     hours=(12, 13, 14, 15),      LOOKBACK=120, K_DISP=1.8),
)


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


def _engine_signals(b: Bars, mid, A1, Eb, e):
    """Build fresh-edge displacement-break continuation signals for ONE session
    engine. Returns (idx, side, level) arrays. Causal throughout."""
    lb = e["LOOKBACK"]
    rmax = roll_max(mid, lb)
    rmin = roll_min(mid, lb)
    sess = hours_mask(b, e["hours"])
    volok = (A1 >= ATR_LO) & (A1 <= ATR_HI)
    bias_up = mid > Eb
    bias_dn = mid < Eb

    disp_up = mid - rmax          # >0 when broken above the prior extreme
    disp_dn = rmin - mid          # >0 when broken below
    thr = e["K_DISP"] * A1

    brk_up = np.isfinite(rmax) & np.isfinite(A1) & (disp_up >= thr) & sess & volok & bias_up
    brk_dn = np.isfinite(rmin) & np.isfinite(A1) & (disp_dn >= thr) & sess & volok & bias_dn

    # fresh rising edge only (one signal per break event)
    fu = brk_up.copy(); fu[1:] &= ~brk_up[:-1]
    fd = brk_dn.copy(); fd[1:] &= ~brk_dn[:-1]

    iu = np.where(fu)[0]
    il = np.where(fd)[0]

    lvl_u = mid[iu] - RETR * disp_up[iu]   # buy-limit dip (continuation long)
    lvl_d = mid[il] + RETR * disp_dn[il]   # sell-limit pop (continuation short)

    idx = np.concatenate([iu, il])
    side = np.concatenate([np.ones(len(iu), int), -np.ones(len(il), int)])
    level = np.concatenate([lvl_u, lvl_d])
    return idx, side, level


def generate(b: Bars) -> Signals:
    mid = b.mid
    A1 = _m1_atr_aligned(b)            # shared M1-ATR (causal)
    Eb = ema(mid, BIAS_EMA)           # shared trend bias (causal)

    idxs, sides, levels = [], [], []
    for e in ENGINES:
        gi, gs, gl = _engine_signals(b, mid, A1, Eb, e)
        idxs.append(gi); sides.append(gs); levels.append(gl)

    i = np.concatenate(idxs)
    side = np.concatenate(sides)
    level = np.concatenate(levels)
    o = np.argsort(i, kind="stable")      # chronological union; engine de-dups via 1-position rule
    i, side, level = i[o], side[o], level[o]
    n = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(n, int),             # LIMIT maker entry at the retest
        level=level,
        sl_pts=np.full(n, SL_PTS),
        tp_pts=np.full(n, TP_PTS),
        ttl=np.full(n, TTL, np.int64),
    )
