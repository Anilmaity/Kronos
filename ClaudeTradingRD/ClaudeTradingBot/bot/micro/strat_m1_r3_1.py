"""r3_1 -- Session-anchored VWAP deviation reversion, BALANCED-regime only (M1 XAU).

CONCEPT (distinct from the dead `m1_band_fade_htf`, which faded a rolling Bollinger
*aligned with* the HTF trend and died at PF 0.745): build a true SESSION-ANCHORED,
VOLUME-WEIGHTED VWAP from the London open, with volume-weighted sigma bands. Fade
extensions beyond Z*sigma back toward VWAP -- BUT ONLY when the regime is BALANCED:
the session VWAP must be roughly FLAT (no trend drift) so we are reverting around a
fair-value magnet, not knife-catching a one-way auction. This is the regime the prior
fades never isolated (2024 gold was a one-way uptrend -> symmetric fading shorts the
trend and dies; the flat-VWAP gate excludes exactly those periods).

Maker limit AT the band earns the spread; target = revert to VWAP; stop = beyond the
band, sigma-scaled. Session-gated to London+NY. The runner grid judges maker AND taker;
the bar is taker-positive @0.25 in BOTH train and OOS.

NO LOOK-AHEAD: VWAP/sigma are cumulative within the *current* session up to and incl.
the decision bar (causal); the balance gate uses only past VWAP values; every entry is
a limit acted on the bar AFTER its decision bar. Absolute imports only.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals
from bot.micro.features import hours_mask

NAME = "m1_svwap_balance_revert"
TF = 60


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


SIM = dict(maxhold=_P("VB_MAXHOLD", 45, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("VB_COOLDOWN", 2, int))

ANCHOR_HOUR = _P("VB_ANCHOR", 7, int)     # session anchor (UTC) = London open
MINBARS = _P("VB_MINBARS", 30, int)       # bars into session before trading
Z_BAND = _P("VB_Z", 2.2)                  # enter beyond Z*sigma
STOP_K = _P("VB_STOPK", 1.3)              # stop = STOP_K*sigma beyond the band
TP_FRAC = _P("VB_TPFRAC", 0.85)           # target = TP_FRAC of the way back to VWAP
FLAT_MAX = _P("VB_FLAT", 0.45)            # |vwap slope over SLOPE_LB| / sigma  must be < this
SLOPE_LB = _P("VB_SLB", 30, int)
SIG_MIN = _P("VB_SIGMIN", 0.6)            # ignore sessions with collapsed sigma (no room)
SIG_MAX = _P("VB_SIGMAX", 12.0)           # ignore blown-out sigma (news/trend)
TTL = _P("VB_TTL", 5, int)
WICK_K = _P("VB_WICK", 0.25)              # pierce beyond band by >= WICK_K*sigma
CLOSE_FRAC = _P("VB_CLOSEFRAC", 0.5)      # wick (beyond) >= this frac of bar range
RETRACE = _P("VB_RETRACE", 0.3)           # maker limit retrace toward the rejected wick
OSC_LB = _P("VB_OSCLB", 30, int)          # window to count VWAP crossings (oscillation)
OSC_MIN = _P("VB_OSCMIN", 3, int)         # require >= this many crossings (true balance)
HTF_EMA = _P("VB_HTFEMA", 240, int)       # slow EMA (M1 bars) for trend veto
HTF_SLB = _P("VB_HTFSLB", 120, int)       # slope lookback for the veto
HTF_VETO = _P("VB_HTFVETO", 0.8)          # |slope|/sigma above this -> veto counter-trend side
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("VB_HOURS", "7,8,9,10,11,12,13,14,15").split(","))


def _grp_cumsum(x, grp):
    """Cumulative sum of x that RESETS at every change of grp. Causal (incl. current)."""
    cs = np.cumsum(x)
    out = cs.copy()
    starts = np.where(grp[1:] != grp[:-1])[0] + 1   # first index of each new group
    if len(starts):
        base = cs[starts - 1]                       # cum value just before the reset
        # forward-fill the base across each group
        b = np.zeros(len(x))
        b[starts] = base
        # build a step function: base value applies from each start to next start
        idx = np.zeros(len(x), np.int64)
        idx[starts] = 1
        seg = np.cumsum(idx)                         # segment id (0 for first group)
        basevals = np.concatenate(([0.0], base))     # seg 0 -> base 0
        out = cs - basevals[seg]
    return out


def _grp_cumcount(grp):
    n = len(grp)
    starts = np.where(grp[1:] != grp[:-1])[0] + 1
    idx = np.zeros(n, np.int64); idx[starts] = 1
    seg = np.cumsum(idx)
    # position within segment
    pos = np.arange(n) - np.concatenate(([0], np.arange(n)[starts]))[seg]
    return pos


def generate(b: Bars) -> Signals:
    mid = b.mid
    vol = b.vol.astype(np.float64)
    vol = np.where(vol > 0, vol, 1.0)               # guard zero-volume bars

    grp = ((b.ts - ANCHOR_HOUR * 3600) // 86400).astype(np.int64)

    sw = _grp_cumsum(vol, grp)
    swm = _grp_cumsum(vol * mid, grp)
    swm2 = _grp_cumsum(vol * mid * mid, grp)
    vwap = swm / sw
    var = swm2 / sw - vwap * vwap
    sigma = np.sqrt(np.clip(var, 0.0, None))
    cnt = _grp_cumcount(grp)

    # balance gate: session VWAP must be ~flat (price reverting, not drifting)
    slope = np.full(b.n, np.nan)
    # compare vwap now vs SLOPE_LB bars ago, only within the same session
    same = np.zeros(b.n, bool)
    same[SLOPE_LB:] = grp[SLOPE_LB:] == grp[:-SLOPE_LB]
    sl = np.full(b.n, np.nan)
    sl[SLOPE_LB:] = vwap[SLOPE_LB:] - vwap[:-SLOPE_LB]
    flat = np.zeros(b.n, bool)
    ok_sig = (sigma > 0) & same & np.isfinite(sl)
    flat[ok_sig] = (np.abs(sl[ok_sig]) / sigma[ok_sig]) < FLAT_MAX

    # oscillation gate: count of sign changes of (mid-vwap) over last OSC_LB bars
    # within the same session -> a genuinely balanced (range) auction crosses VWAP often.
    dev_sign = np.sign(mid - vwap)
    cross = np.zeros(b.n)
    cross[1:] = ((dev_sign[1:] != dev_sign[:-1]) & (grp[1:] == grp[:-1])).astype(float)
    from numpy.lib.stride_tricks import sliding_window_view as _swv
    osc = np.zeros(b.n)
    if b.n > OSC_LB:
        osc[OSC_LB:] = _swv(cross[:-1], OSC_LB).sum(axis=1)
    osc_ok = osc >= OSC_MIN

    sess = hours_mask(b, SESSION_HOURS)
    base = (cnt >= MINBARS) & sess & flat & osc_ok & (sigma >= SIG_MIN) & (sigma <= SIG_MAX)

    upper = vwap + Z_BAND * sigma
    lower = vwap - Z_BAND * sigma

    # mid-bar high/low approximations (engine convention)
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    rng = np.maximum(hi - lo, 1e-9)
    # rejection: pierce beyond band by >= WICK_K*sigma, then CLOSE back inside the band,
    # with the close in the reverting portion of the bar (genuine wick rejection).
    pierce_up = (hi >= upper + WICK_K * sigma) & (mid < upper) & ((upper - mid) >= 0) \
        & ((hi - mid) / rng >= CLOSE_FRAC)
    pierce_dn = (lo <= lower - WICK_K * sigma) & (mid > lower) & ((mid - lower) >= 0) \
        & ((mid - lo) / rng >= CLOSE_FRAC)

    # HTF trend veto: never fade AGAINST a strong slow trend (kills the short-the-rip
    # losses in a one-way uptrend, and vice-versa). Causal EMA + past-only slope.
    from bot.micro.features import ema as _ema
    htf = _ema(mid, HTF_EMA)
    hslope = np.full(b.n, np.nan)
    hslope[HTF_SLB:] = htf[HTF_SLB:] - htf[:-HTF_SLB]
    sig_safe = np.where(sigma > 0, sigma, np.nan)
    strong_up = np.isfinite(hslope) & ((hslope / sig_safe) >= HTF_VETO)
    strong_dn = np.isfinite(hslope) & ((hslope / sig_safe) <= -HTF_VETO)

    short_ok = base & pierce_up & ~strong_up   # don't short into a strong uptrend
    long_ok = base & pierce_dn & ~strong_dn

    iu = np.where(short_ok)[0]
    il = np.where(long_ok)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    # maker limit: a small retrace back toward the band edge after the rejection bar
    lvl_s = mid[iu] + RETRACE * (hi[iu] - mid[iu])
    lvl_l = mid[il] - RETRACE * (mid[il] - lo[il])
    level = np.concatenate([lvl_s, lvl_l])

    # target: TP_FRAC of the way back to VWAP from the entry level ; stop: beyond the wick
    tp_s = TP_FRAC * (lvl_s - vwap[iu])
    tp_l = TP_FRAC * (vwap[il] - lvl_l)
    tp = np.concatenate([tp_s, tp_l])
    sl_s = (hi[iu] - lvl_s) + STOP_K * sigma[iu]
    sl_l = (lvl_l - lo[il]) + STOP_K * sigma[il]
    slp = np.concatenate([sl_s, sl_l])

    o = np.argsort(i, kind="stable")
    i, side, level, tp, slp = i[o], side[o], level[o], tp[o], slp[o]
    n = len(i)
    # guard degenerate tp/sl
    tp = np.clip(tp, 0.4, None)
    slp = np.clip(slp, 0.6, None)
    return Signals(i=i, side=side, kind=np.ones(n, int), level=level,
                   sl_pts=slp, tp_pts=tp, ttl=np.full(n, TTL, np.int64))
