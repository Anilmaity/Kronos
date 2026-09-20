"""M1 SESSION-LIQUIDITY SWEEP REVERSAL (Asian-range Judas fade back into the range).

CONCEPT (distinct from the dead m1_sweep_reversal which used rolling-fractal swings
and traded WITH the trend as a continuation): the liquidity pool here is a *session*
extreme -- the Asian-session high/low (00:00-06:59 UTC), genuine resting liquidity
that London/NY hunts. During London/NY, price SWEEPS one side of that range (pokes a
little beyond it to grab stops), then DISPLACES back through the level (close reclaims
inside with a rejection wick). We FADE the sweep -- stop just beyond the sweep extreme,
target an interior-directed TP_R multiple of the stop. M1 bars (~2pt) give it room.

HONEST RESULT (research deliverable, NOT a pass): across ~600 configs (every target
type, stop, wick, sweep buffer, HTF bias with/against, side, hour-set, and a
displacement-confirmation), TRAIN taker PF at ~0.25 spread caps at ~0.75 -- the fade
has no edge in the relentless 2024-2025 uptrend. diag_ss.py shows the only favorable
asymmetry is the SHORT side (high-sweep fade, +0.5pt mean cost-free); the LONG side is
net NEGATIVE (-1.4..-1.9pt), so this is baked SHORT-ONLY. Even so it is TRAIN-NEGATIVE
/ OOS-POSITIVE (taker PF ~0.75 train vs ~1.11 OOS) -- exactly the regime-fit pattern
GOAL.md rejects -- and fires ~1/day. CONCLUSION: the M1 session-sweep reversal does NOT
clear the bar; consistent with FINDINGS.md, the XAU sweep/fade family has no robust
taker edge. The default below is the least-bad honest representative, not a survivor.

WHY THIS CAN HAVE ASYMMETRY (scout #2/#3): a bare rolling-extreme fade is symmetric.
Here the trigger is narrowed to (a) a *session* level = real resting liquidity that
institutions target, (b) a marginal sweep that pokes beyond then (c) reclaims with a
rejection wick = failed breakout, and (d) only the FIRST sweep of each side per day
(freshness). After a failed sweep of the Asian high, the path of least resistance is
back into the range -- favorable >> adverse.

NO LOOK-AHEAD: the Asian range for a UTC day is built only from bars with hod in
[0,7); it is referenced ONLY at hod>=7 (all Asian bars precede every trade bar that
day), so it is fully formed and causal. ATR is causal. Entries act on the bar AFTER
the sweep, filled by the engine next-bar+. Absolute imports.
CONTRACT: generate(b)->Signals, SIM, NAME, TF.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals, atr as atr_fn
from bot.micro.features import hours_mask

NAME = "m1_session_sweep_revert"
TF = 60   # M1


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


KIND     = _P("SS_KIND", 1, int)        # 0=market on reclaim bar, 1=limit retest at level
SIM = dict(maxhold=_P("SS_MAXHOLD", 60, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("SS_COOLDOWN", 1, int))

ATR_P    = _P("SS_ATRP", 20, int)       # M1 ATR period
SWEEP_BUF= _P("SS_SWBUF", 0.40)         # sweep must exceed level by >= this * ATR
MAXPEN   = _P("SS_MAXPEN", 2.5)         # sweep pokes at most this * ATR beyond (marginal)
WICK_K   = _P("SS_WICK", 0.30)          # rejection wick (extreme-close) >= WICK_K * ATR
RECLAIM_K= _P("SS_RECK", 0.02)          # close must be this * ATR back inside the level
SL_BUF   = _P("SS_SLBUF", 1.00)         # stop sits SL_BUF*ATR beyond the sweep extreme
TP_R     = _P("SS_TPR", 4.0)            # target = TP_R * stop distance (interior-directed)
RR_MIN   = _P("SS_RRMIN", 0.5)          # skip if target/stop reward:risk below this
RR_MAX   = _P("SS_RRMAX", 12.0)         # cap reward:risk (skip absurd geometry)
RNG_LO   = _P("SS_RNGLO", 4.0)          # min Asian range (pts) -- skip dead nights
RNG_HI   = _P("SS_RNGHI", 45.0)         # max Asian range (pts) -- skip runaway nights
ATR_LO   = _P("SS_ATRLO", 0.5)          # min M1 ATR (avoid dead tape)
ATR_HI   = _P("SS_ATRHI", 14.0)
SL_MIN   = _P("SS_SLMIN", 0.8)          # min stop distance (pts)
SL_MAX   = _P("SS_SLMAX", 8.0)          # max stop distance (pts)
TTL      = _P("SS_TTL", 8, int)         # retest limit lifetime (M1 bars) -- KIND=1 only
SIDE_ONLY= _P("SS_SIDE", -1, int)       # 0=both, 1=long-only, -1=short-only
ASIA_A   = _P("SS_ASIA_A", 0, int)
ASIA_Z   = _P("SS_ASIA_Z", 7, int)
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("SS_HOURS", "7,8,9,10,11,12,13,14").split(","))


def _session_range(b, hi, lo):
    """Per-UTC-day Asian (hod in [ASIA_A,ASIA_Z)) high/low, broadcast to every bar of
    that day. Used only at hod>=ASIA_Z, so it is complete & causal there."""
    n = b.n
    day = b.day
    aH = np.full(n, np.nan); aL = np.full(n, np.nan)
    chg = np.concatenate(([0], np.where(np.diff(day) != 0)[0] + 1, [n]))
    hod = b.hod
    for k in range(len(chg) - 1):
        s, e = int(chg[k]), int(chg[k + 1])
        m = (hod[s:e] >= ASIA_A) & (hod[s:e] < ASIA_Z)
        if m.any():
            aH[s:e] = hi[s:e][m].max()
            aL[s:e] = lo[s:e][m].min()
    return aH, aL


def _first_per_day(idx, day):
    """Keep only the first signal index within each UTC day (freshness)."""
    if len(idx) == 0:
        return idx
    d = day[idx]
    keep = np.ones(len(idx), bool)
    keep[1:] = d[1:] != d[:-1]
    return idx[keep]


def _empty():
    z = np.zeros(0)
    return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)


def generate(b: Bars) -> Signals:
    n = b.n
    if n < 200:
        return _empty()
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    c  = b.mid
    A  = atr_fn(b, ATR_P)
    a  = np.where(np.isfinite(A) & (A > 0), A, np.nan)

    aH, aL = _session_range(b, hi, lo)
    rng = aH - aL
    mid = (aH + aL) * 0.5

    sess = hours_mask(b, SESSION_HOURS)
    volok = np.isfinite(a) & (a >= ATR_LO) & (a <= ATR_HI)
    rngok = np.isfinite(rng) & (rng >= RNG_LO) & (rng <= RNG_HI)
    base = sess & volok & rngok & np.isfinite(aH)

    # ---- SHORT: sweep of Asian HIGH, reclaim back below, fade into range ----
    sweepH = base & (hi >= aH + SWEEP_BUF * a) & (hi <= aH + MAXPEN * a) \
        & (c <= aH - RECLAIM_K * a) & ((hi - c) >= WICK_K * a)
    iH = np.where(sweepH)[0]
    iH = _first_per_day(iH, b.day)
    if SIDE_ONLY > 0:
        iH = iH[:0]

    # ---- LONG: sweep of Asian LOW, reclaim back above, fade into range ----
    sweepL = base & (lo <= aL - SWEEP_BUF * a) & (lo >= aL - MAXPEN * a) \
        & (c >= aL + RECLAIM_K * a) & ((c - lo) >= WICK_K * a)
    iL = np.where(sweepL)[0]
    iL = _first_per_day(iL, b.day)
    if SIDE_ONLY < 0:
        iL = iL[:0]

    if len(iH) + len(iL) == 0:
        return _empty()

    # entry level: limit retest at the swept session level (KIND=1) or close (KIND=0)
    if KIND == 1:
        lvH = aH[iH]; lvL = aL[iL]
    else:
        lvH = c[iH]; lvL = c[iL]

    # stop beyond the sweep extreme; target = TP_R * stop, directed into the range
    slH = (hi[iH] - lvH) + SL_BUF * a[iH]
    slL = (lvL - lo[iL]) + SL_BUF * a[iL]
    tpH = TP_R * slH          # short: distance down from the high level into the interior
    tpL = TP_R * slL

    i = np.concatenate([iH, iL])
    side = np.concatenate([-np.ones(len(iH), np.int64), np.ones(len(iL), np.int64)])
    level = np.concatenate([lvH, lvL])
    slp = np.concatenate([slH, slL])
    tpp = np.concatenate([tpH, tpL])

    # geometry filters
    rr = tpp / np.where(slp > 0, slp, np.nan)
    ok = np.isfinite(rr) & (slp >= SL_MIN) & (slp <= SL_MAX) \
        & (rr >= RR_MIN) & (rr <= RR_MAX) & (tpp > 0)
    i, side, level, slp, tpp = i[ok], side[ok], level[ok], slp[ok], tpp[ok]
    if len(i) == 0:
        return _empty()

    o = np.argsort(i, kind="stable")
    i, side, level, slp, tpp = i[o], side[o], level[o], slp[o], tpp[o]
    m = len(i)
    return Signals(i=i, side=side, kind=np.full(m, KIND, np.int8), level=level,
                   sl_pts=slp, tp_pts=tpp, ttl=np.full(m, TTL, np.int64))
