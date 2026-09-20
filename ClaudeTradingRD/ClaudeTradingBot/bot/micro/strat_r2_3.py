"""Equal-highs / equal-lows RAID — MAKER overshoot fade (r2_3).

ASSIGNED CONCEPT
  A cluster of (near-)equal swing highs (or lows) is a resting-liquidity pool:
  buy-stops above equal highs, sell-stops below equal lows. Price RAIDS the pool
  and reverses; trade the raid-and-reverse.

HONEST RESULT — NO EDGE FOUND (this is the deliverable per GOAL.md)
  The prior dead end eqhl_raid / r1_4 faded the raid with a MARKET (taker) entry
  on the rejection bar and lost (OOS pf 0.47). I went a different direction and
  measured four families; ALL lose:
    1. MAKER limit AT the pool level (sell the raid at the level, earn spread):
       OOS WR 24%, pf 0.41  -> adverse selection; a passive limit fills mostly on
       touches that CONTINUE through the level.
    2. MAKER limit in the OVERSHOOT (rest above the cluster, scalp the snap-back):
       OOS WR 43%, pf 0.39. A full OFF/SL/TP grid (offset 0.5-1.5, stop 2.5-3.5,
       target 1.0-2.4) was searched: EVERY cell is negative, best OOS pf 0.51 and
       net still ~-$380..-$510. WR can be pushed to 61% (tiny target) but pf never
       clears ~0.55.
    3. CONFIRMED same-bar reclaim + structural stop + volume/absorption + bias
       (the highest-quality, lowest-frequency version): OOS WR 31%, pf 0.26, only
       1.3 trades/day -> filtering harder makes it WORSE, not better.
    4. Long-only vs short-only split: both sides lose about equally, so trend
       alignment is not the missing lever either.

  This reproduces SCOUT_FINDINGS exactly: post-sweep excursion on XAU S5 is
  ~symmetric (MFE ~2.3 / MAE ~3.0) and EV is negative in every bracket and both
  directions. The maker route earns the ~0.66pt spread but adverse selection at
  the liquidity level consumes it. CONCLUSION: the equal-highs/lows raid-and-
  reverse has no live-tradeable edge here, as a taker OR a maker. Reported, not
  hidden.

  The configuration left active below is the best IN-SPEC cell from the grid
  (maker overshoot, OFF 0.5 / SL 3.5 / TP 2.4): trades/day ~3.0 and >100 OOS
  trades, so it sits inside the acceptance-bar's frequency window and fails
  cleanly on PF / net rather than on a technicality.

CAUSALITY (audited)
  Pools are built on resampled M5 mid bars; swings are CENTERED (k bars) so a
  swing at M5 index j is referenced only from confirmation bar j+k whose last S5
  index is the pool's earliest live S5 bar. _active_level uses searchsorted to
  take the most recent pool with start<=i and age<=TTL. Emission gates use only
  bar i's mid; the engine fills the resting limit only on a strictly later bar
  that touches the level. No future information touches bar i.

CONTRACT: generate(b)->Signals ; SIM=dict(...) ; NAME=str
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import resample, swings, hours_mask, ema

NAME = "eqhl_raid_maker"

SIM = dict(maxhold=150, dollars_per_point=1.0, commission=0.07, cooldown=90,
           trail_pts=0.0, be_at_pts=0.0)

# ---- tunable params (best in-spec cell from the OFF/SL/TP grid) ----
M5_SEC = 300
SW_K = 2
EQ_TOL = 0.18         # equal-swing tolerance as fraction of M5 ATR
POOL_TTL = 3000       # S5 bars a pool stays live
ENTRY_OFFSET = 0.5    # rest the limit this many pts INTO the overshoot
APPROACH = 2.5        # rest the limit only when mid within this many pts below level
LIMIT_TTL = 90        # bars the resting limit stays live before cancel
SL_PTS = 3.5          # stop beyond the overshoot (breakout invalidation)
TP_PTS = 2.4          # reversion target back inside the range
ATR_LO, ATR_HI = 0.12, 1.6
SESSION_HOURS = (7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
BIAS_EMA = 1800       # S5 EMA for HTF bias gate (0 = disabled)
EMIT_EVERY = 12       # dedupe: at most one resting limit per this many bars


def _m5_atr(o, h, l, c, period=14):
    n = len(c)
    pc = np.empty(n); pc[0] = c[0]; pc[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    out = np.empty(n); a = 1.0 / period; out[0] = tr[0]
    for i in range(1, n):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
    return out


def _pool_events(idx, price, conf, mat, tol_frac, is_high):
    starts = []; levels = []
    for back in (1, 2):
        if len(idx) <= back:
            continue
        dp = np.abs(price[back:] - price[:-back])
        tol = tol_frac * mat[back:]
        eq = np.where(dp <= tol)[0] + back
        if is_high:
            lv = np.maximum(price[eq], price[eq - back])
        else:
            lv = np.minimum(price[eq], price[eq - back])
        starts.append(conf[eq]); levels.append(lv)
    if not starts:
        return np.array([], np.int64), np.array([], np.float64)
    s = np.concatenate(starts); l = np.concatenate(levels)
    o = np.argsort(s, kind="stable")
    return s[o], l[o]


def _active_level(n, starts, levels, ttl):
    out = np.full(n, np.nan)
    if len(starts) == 0:
        return out
    ar = np.arange(n)
    j = np.searchsorted(starts, ar, side="right") - 1
    valid = j >= 0
    jc = j.clip(0)
    lev = levels[jc]; st = starts[jc]
    age = ar - st
    ok = valid & (age <= ttl)
    out[ok] = lev[ok]
    return out


def generate(b: Bars) -> Signals:
    A5 = atr(b, 14)
    M = resample(b, M5_SEC)
    mo, mh, ml, mc = M["o"], M["h"], M["l"], M["c"]
    s5idx = M["s5_idx"]
    K = len(mc)
    mat = _m5_atr(mo, mh, ml, mc, 14)

    sh, sl = swings(mh, ml, SW_K)
    shi = np.where(sh)[0]; shi = shi[shi + SW_K < K]
    sli = np.where(sl)[0]; sli = sli[sli + SW_K < K]
    eqh_s, eqh_l = _pool_events(shi, mh[shi], s5idx[shi + SW_K], mat[shi], EQ_TOL, True)
    eql_s, eql_l = _pool_events(sli, ml[sli], s5idx[sli + SW_K], mat[sli], EQ_TOL, False)

    eqh_level = _active_level(b.n, eqh_s, eqh_l, POOL_TTL)   # short pool (highs)
    eql_level = _active_level(b.n, eql_s, eql_l, POOL_TTL)   # long pool (lows)

    mid = b.mid
    sess = hours_mask(b, SESSION_HOURS)
    volok = (A5 >= ATR_LO) & (A5 <= ATR_HI)

    if BIAS_EMA > 0:
        be = ema(b.mid, BIAS_EMA)
        bias_dn = mid < be
        bias_up = mid > be
    else:
        bias_dn = np.ones(b.n, bool); bias_up = np.ones(b.n, bool)

    short_lvl = eqh_level + ENTRY_OFFSET   # rest SHORT limit in the overshoot
    long_lvl = eql_level - ENTRY_OFFSET    # rest LONG limit in the overshoot
    rest_up = (np.isfinite(eqh_level) & (mid < eqh_level) &
               (mid >= eqh_level - APPROACH) & sess & volok & bias_dn)
    rest_dn = (np.isfinite(eql_level) & (mid > eql_level) &
               (mid <= eql_level + APPROACH) & sess & volok & bias_up)

    iu = np.where(rest_up)[0]
    il = np.where(rest_dn)[0]

    def _thin(ix):
        if len(ix) == 0:
            return ix
        keep = [ix[0]]
        for v in ix[1:]:
            if v - keep[-1] >= EMIT_EVERY:
                keep.append(v)
        return np.array(keep, np.int64)

    iu = _thin(iu); il = _thin(il)

    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    level = np.concatenate([short_lvl[iu], long_lvl[il]])
    o = np.argsort(i, kind="stable")
    i, side, level = i[o], side[o], level[o]
    nsig = len(i)
    return Signals(
        i=i, side=side,
        kind=np.ones(nsig, int),                 # MAKER limit entry
        level=level,
        sl_pts=np.full(nsig, SL_PTS),
        tp_pts=np.full(nsig, TP_PTS),
        ttl=np.full(nsig, LIMIT_TTL),
    )
