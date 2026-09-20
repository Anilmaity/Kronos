"""M1 z-score fade — SELECTIVE session liquidity-grab reversion, measured move.

CONCEPT (mean-reversion family, distilled from ~120 failed band-fade configs in this
round). A generic Bollinger z-fade is decisively TRAIN-NEGATIVE at 0.25 taker on XAU:
the per-bar excursion after a z>=2 break is ~symmetric (MFE/MAE ~1.05-1.17, measured)
so trading it 5-20x/day just pays the spread into noise. The ONLY fade structure that
showed a real two-window pulse in prior research was the once-per-session liquidity
grab faded back through the range. This is its Bollinger expression:

A short fires at most once per session per day when, INSIDE a session window:
  1) the bar pokes to a NEW running session high (a buy-side liquidity grab), AND
  2) it is a Bollinger extreme: z = (mid-mean)/std >= Z_IN, AND
  3) it is COUNTER to the higher-TF bias (EMA50<EMA200) -> the grab is a manipulation
     leg likely to fail and revert WITH the dominant flow.
Entry  : MARKET next bar (taker; deployable on a market-execution account).
Stop   : SL_K * ATR beyond entry (structure stop above the grab).
Target : TP_K * ATR measured move back through the range (TP_K > SL_K -> R>1), so a
         modest win rate still clears costs. Long is the exact mirror (sell-side grab
         in an uptrend, fade long).

Honesty: this round's scans show even this selective fade only approaches break-even;
it does NOT robustly clear the 1.15-train / 1.3-OOS taker bar. The runner JSON is the
verdict. No look-ahead: session hi/lo are running maxima over PRIOR in-session bars,
z/ATR/EMA are causal, entry is the engine's next-bar market fill; one decision per
session is taken at the bar it forms.
"""
import numpy as np
from bot.micro.engine import Bars, Signals, atr
from bot.micro.features import ema

NAME = "m1_session_grab_zfade"
TF = 60   # M1 execution timeframe (seconds)

SIM = dict(maxhold=180, dollars_per_point=1.0, commission=0.07, cooldown=0)

LB = 20           # Bollinger window (causal)
Z_IN = 2.0        # extreme threshold
EMA_FAST = 50
EMA_SLOW = 200
ATR_P = 14
SL_K = 3.0        # stop  = SL_K * ATR  (wide enough to survive the grab's noise)
TP_K = 3.5        # target = TP_K * ATR (measured move back through the range, R>1)
# session windows (start_hour, end_hour) UTC; one trade per window per day
SESSIONS = [(7, 11), (12, 16)]


def _roll_mean_std(x, w):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    mean = np.full(len(x), np.nan); std = np.full(len(x), np.nan)
    if len(x) > w:
        win = swv(x[:-1], w)
        mean[w:] = win.mean(axis=1); std[w:] = win.std(axis=1)
    return mean, std


def generate(b: Bars) -> Signals:
    n = b.n
    mid = b.mid
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    av = atr(b, ATR_P)
    ef = ema(mid, EMA_FAST); es = ema(mid, EMA_SLOW)
    bias = np.sign(ef - es)
    mean, std = _roll_mean_std(mid, LB)
    z = (mid - mean) / np.where(std > 0, std, np.nan)
    hod = b.hod; day = b.day

    I, SIDE, SLP, TPP = [], [], [], []
    for dy in np.unique(day):
        didx = np.where(day == dy)[0]
        if len(didx) == 0:
            continue
        h = hod[didx]
        for (h0, h1) in SESSIONS:
            w = didx[(h >= h0) & (h < h1)]
            if len(w) < 5:
                continue
            run_hi = -1e18; run_lo = 1e18
            taken = False
            for j in w:
                if taken:
                    break
                ok = (np.isfinite(z[j]) and np.isfinite(av[j]) and av[j] > 0
                      and np.isfinite(bias[j]))
                # short: new session high + extreme up + downtrend bias
                if ok and hi[j] > run_hi and z[j] >= Z_IN and bias[j] < 0:
                    I.append(j); SIDE.append(-1)
                    SLP.append(SL_K * av[j]); TPP.append(TP_K * av[j]); taken = True
                # long: new session low + extreme down + uptrend bias
                elif ok and lo[j] < run_lo and z[j] <= -Z_IN and bias[j] > 0:
                    I.append(j); SIDE.append(1)
                    SLP.append(SL_K * av[j]); TPP.append(TP_K * av[j]); taken = True
                if hi[j] > run_hi:
                    run_hi = hi[j]
                if lo[j] < run_lo:
                    run_lo = lo[j]

    if not I:
        e = np.array([], np.float64); ei = np.array([], np.int64)
        return Signals(i=ei, side=ei, kind=ei, level=e, sl_pts=e, tp_pts=e, ttl=ei)
    I = np.array(I, np.int64)
    o = np.argsort(I, kind="stable")
    I = I[o]
    SIDE = np.array(SIDE, np.int8)[o]
    SLP = np.array(SLP, np.float64)[o]
    TPP = np.array(TPP, np.float64)[o]
    m = len(I)
    return Signals(i=I, side=SIDE, kind=np.zeros(m, int), level=mid[I],
                   sl_pts=SLP, tp_pts=TPP, ttl=np.zeros(m, np.int64))
