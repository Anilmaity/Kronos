"""r2_4 — HTF-trend-aligned Bollinger band-fade (maker) for M1 XAU.

CONCEPT: rest a maker limit AT the band extreme (mean -/+ Z*std) — a true Bollinger
fade that earns the spread — but take ONLY the side aligned with the higher-TF mean
(buy the lower band only while the slow HTF EMA is rising; sell the upper band only
while it is falling). This sidesteps the regime trap that sank prior fades (2024 was a
one-way gold uptrend, so symmetric fading shorts the trend and dies in train). Target
= revert to the M1 mean; stop = structure-wide beyond the band. Session-gated to
London+NY. Grid judges maker AND taker; the bar is taker-positive in BOTH windows.

NO LOOK-AHEAD: rolling mean/std exclude the current bar; HTF EMA + slope are past-only;
every entry is a limit acted on the bar AFTER its decision bar. Absolute imports.
"""
import os
import numpy as np
from bot.micro.engine import Bars, Signals
from bot.micro.features import hours_mask, ema

NAME = "m1_band_fade_htf"
TF = 60


def _P(name, default, cast=float):
    v = os.environ.get(name)
    return cast(v) if v is not None else default


SIM = dict(maxhold=_P("MR_MAXHOLD", 30, int), dollars_per_point=1.0, commission=0.07,
           cooldown=_P("MR_COOLDOWN", 1, int))

LOOKBACK = _P("MR_LB", 40, int)
Z_BAND   = _P("MR_Z", 2.0)
HTF_EMA  = _P("MR_HTF", 120, int)
SLOPE_LB = _P("MR_SLB", 30, int)
SLOPE_MIN = _P("MR_SLMIN", 0.3)   # |htf slope|/atr to call a trend
SL_PTS   = _P("MR_SL", 3.0)
TP_MIN   = _P("MR_TPMIN", 1.0)
TP_MAX   = _P("MR_TPMAX", 4.0)
TTL      = _P("MR_TTL", 4, int)
ATR_LB   = _P("MR_ATRLB", 14, int)
ALIGN    = _P("MR_ALIGN", 1, int)   # 1: only fade WITH htf trend; 0: both sides
SESSION_HOURS = tuple(int(x) for x in
                      os.environ.get("MR_HOURS", "7,8,9,10,11,12,13,14,15").split(","))


def _roll_mean_std(x, w):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    mean = np.full(len(x), np.nan); std = np.full(len(x), np.nan)
    if len(x) > w:
        win = swv(x[:-1], w)
        mean[w:] = win.mean(axis=1)
        std[w:] = win.std(axis=1)
    return mean, std


def _m1_atr(b: Bars, period):
    hi = (b.ah + b.bh) * 0.5; lo = (b.al + b.bl) * 0.5; c = b.mid
    pc = np.empty(b.n); pc[0] = c[0]; pc[1:] = c[:-1]
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - pc), np.abs(lo - pc)))
    out = np.empty(b.n); a = 1.0 / period; out[0] = tr[0]
    for i in range(1, b.n):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
    return out


def generate(b: Bars) -> Signals:
    mid = b.mid
    mean, std = _roll_mean_std(mid, LOOKBACK)
    atrv = _m1_atr(b, ATR_LB)
    htf = ema(mid, HTF_EMA)
    slope = np.full(b.n, np.nan)
    slope[SLOPE_LB:] = (htf[SLOPE_LB:] - htf[:-SLOPE_LB]) / np.where(atrv[SLOPE_LB:] > 0, atrv[SLOPE_LB:], np.nan)
    sess = hours_mask(b, SESSION_HOURS)

    lower = mean - Z_BAND * std
    upper = mean + Z_BAND * std
    base = np.isfinite(std) & np.isfinite(slope) & sess & (atrv > 0) & (std > 0)

    up = slope >= SLOPE_MIN
    dn = slope <= -SLOPE_MIN
    if ALIGN > 0:
        long_ok = base & up      # buy lower band only in uptrend
        short_ok = base & dn     # sell upper band only in downtrend
    else:
        long_ok = base
        short_ok = base

    il = np.where(long_ok)[0]; iu = np.where(short_ok)[0]
    i = np.concatenate([iu, il])
    side = np.concatenate([-np.ones(len(iu), int), np.ones(len(il), int)])
    level = np.concatenate([upper[iu], lower[il]])
    # mean-revert target: band -> mean distance, clipped
    tp_s = np.clip(upper[iu] - mean[iu], TP_MIN, TP_MAX)
    tp_l = np.clip(mean[il] - lower[il], TP_MIN, TP_MAX)
    tp = np.concatenate([tp_s, tp_l])

    o = np.argsort(i, kind="stable")
    i, side, level, tp = i[o], side[o], level[o], tp[o]
    n = len(i)
    return Signals(i=i, side=side, kind=np.ones(n, int), level=level,
                   sl_pts=np.full(n, SL_PTS), tp_pts=tp,
                   ttl=np.full(n, TTL, np.int64))
