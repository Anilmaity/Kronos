"""Micro-BOS continuation via RETEST limit entry (r2_2).

CONCEPT
  A *displacement* break of micro-structure: the mid closes beyond the prior
  N-bar extreme by more than k*ATR (a genuine momentum break, not a 1-tick poke).
  We do NOT chase the breakout (scout: bare breakouts are symmetric noise, and the
  prior market-entry `micro_bos_cont` lost). Instead we sit a LIMIT order into a
  *shallow retrace* of the displacement leg and join the continuation at a discount.
  The limit entry earns the spread (scout #4) which is the margin that turns a thin
  asymmetry positive; entry is filtered to HTF-aligned, active-session, sane-vol context.

WHY THIS IS DIFFERENT FROM THE DEAD micro_bos_cont
  - Limit retest entry (kind=1) instead of market chase -> earns spread, better price.
  - HTF (M5 EMA) bias gate: only continue WITH the higher-TF trend.
  - Real displacement threshold (k*ATR) + vol band + session -> far fewer, cleaner trades.

CAUSALITY
  Everything at decision bar i uses info up to close[i]. HTF bias is mapped from
  *completed* M5 bars only (searchsorted on the last S5 index of each M5 bar, strict).
  The limit fill is resolved forward by the engine (no look-ahead).
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr, roll_max, roll_min
from bot.micro.features import resample, ema, hours_mask

NAME = "micro_bos_retest"

SIM = dict(maxhold=120, dollars_per_point=1.0, commission=0.07, cooldown=60)

# --- tunable params (runner sweeps vary these +/-30%) ---
LOOKBACK = 40           # bars defining the micro-structure extreme
K_DISP = 1.0            # displacement must clear the extreme by K_DISP*ATR
PULL_ATR = 1.0          # limit sits PULL_ATR*ATR back into the displacement leg
ATR_LO, ATR_HI = 0.25, 1.5
SL_PTS = 2.0            # 1:1 R — no high-WR / tiny-TP illusion
TP_PTS = 2.0
TTL = 60                # bars the retest limit stays live
HTF_SEC = 300           # M5 for bias
EMA_FAST, EMA_SLOW = 10, 30
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15)   # London + NY (UTC)


def _htf_bias(b: Bars, n):
    """Causal HTF up/down bias per S5 bar from completed M5 EMA cross."""
    m5 = resample(b, HTF_SEC)
    ef = ema(m5["c"], EMA_FAST)
    es = ema(m5["c"], EMA_SLOW)
    up = ef > es
    last = m5["s5_idx"]                       # last S5 index of each M5 bar
    pos = np.searchsorted(last, np.arange(n), side="left") - 1   # strict: M5 done before t
    bias = np.zeros(n, np.int8)
    ok = pos >= 0
    bias[ok] = np.where(up[pos[ok]], 1, -1)
    return bias


def generate(b: Bars) -> Signals:
    n = b.n
    A = atr(b, 14)
    rmax = roll_max(b.mid, LOOKBACK)
    rmin = roll_min(b.mid, LOOKBACK)
    bias = _htf_bias(b, n)
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A >= ATR_LO) & (A <= ATR_HI)

    disp_up = (b.mid > rmax + K_DISP * A) & np.isfinite(rmax) & sess & volok & (bias > 0)
    disp_dn = (b.mid < rmin - K_DISP * A) & np.isfinite(rmin) & sess & volok & (bias < 0)

    iu = np.where(disp_up)[0]
    il = np.where(disp_dn)[0]

    # limit retest levels: a shallow pullback into the just-made leg
    lvl_u = b.mid[iu] - PULL_ATR * A[iu]      # buy below current close
    lvl_d = b.mid[il] + PULL_ATR * A[il]      # sell above current close

    i = np.concatenate([iu, il])
    side = np.concatenate([np.ones(len(iu), int), -np.ones(len(il), int)])
    level = np.concatenate([lvl_u, lvl_d])
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    m = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(m, int),                 # LIMIT (maker) retest entry
        level=level,
        sl_pts=np.full(m, SL_PTS),
        tp_pts=np.full(m, TP_PTS),
        ttl=np.full(m, TTL),
    )
