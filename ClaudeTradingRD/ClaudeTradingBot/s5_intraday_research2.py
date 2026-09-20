"""ROUND 2: improve weekly consistency via (1) higher-TF bias filter and
(2) PORTFOLIO diversification of several small intraday edges.

Reuses load/evaluate/indicators from s5_intraday_research. Same taker cost 0.35pt.
"""
import datetime as dt
from collections import deque

from s5_intraday_research import load, evaluate, strat_orb, COST_PT


def ema_series(vals, n):
    k = 2 / (n + 1); out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def bias_long_short(close, n_long=240, slope_lk=48):
    """Higher-TF proxy from M5: EMA(n_long) level + slope. +1 up, -1 down, 0 flat."""
    e = ema_series(close, n_long)
    b = [0] * len(close)
    for i in range(len(close)):
        if i < n_long + slope_lk:
            continue
        up = close[i] > e[i] and e[i] > e[i - slope_lk]
        dn = close[i] < e[i] and e[i] < e[i - slope_lk]
        b[i] = 1 if up else (-1 if dn else 0)
    return b


def strat_orb_biased(bars, *, sessions=((7, 7, 30), (13, 13, 30)), or_min=30,
                     tp_mult=1.5, hold_bars=36, n_long=240):
    """ORB but only take breaks ALIGNED with the higher-TF bias."""
    t = [b[0] for b in bars]; o = [b[1] for b in bars]; h = [b[2] for b in bars]
    lo = [b[3] for b in bars]; c = [b[4] for b in bars]
    n = len(c); bias = bias_long_short(c, n_long)
    by_day = {}
    for idx, tt in enumerate(t):
        by_day.setdefault(tt.date(), []).append(idx)
    trades = []
    for day, idxs in by_day.items():
        for (sh, _eh, _em) in sessions:
            or_idx = [k for k in idxs if t[k].hour == sh and t[k].minute < or_min]
            if len(or_idx) < 2:
                continue
            rng_hi = max(h[k] for k in or_idx); rng_lo = min(lo[k] for k in or_idx)
            rng = rng_hi - rng_lo
            if rng <= 0:
                continue
            start = or_idx[-1] + 1
            side = None
            for k in range(start, min(start + hold_bars, n)):
                if t[k].date() != day:
                    break
                bdir = bias[k]
                if h[k] >= rng_hi and side is None and bdir == 1:
                    side = "long"; entry = rng_hi; stop = rng_lo
                    tp = rng_hi + tp_mult * rng; ek = k; break
                if lo[k] <= rng_lo and side is None and bdir == -1:
                    side = "short"; entry = rng_lo; stop = rng_hi
                    tp = rng_lo - tp_mult * rng; ek = k; break
            if side is None:
                continue
            exit_px = None
            for k in range(ek + 1, min(ek + hold_bars, n)):
                if t[k].date() != day:
                    exit_px = c[k - 1]; break
                if side == "long":
                    if lo[k] <= stop:
                        exit_px = stop; break
                    if h[k] >= tp:
                        exit_px = tp; break
                else:
                    if h[k] >= stop:
                        exit_px = stop; break
                    if lo[k] <= tp:
                        exit_px = tp; break
            if exit_px is None:
                exit_px = c[min(ek + hold_bars, n - 1)]
            gross = (exit_px - entry) if side == "long" else (entry - exit_px)
            trades.append({"t": t[ek], "gross": gross})
    trades.sort(key=lambda x: x["t"])
    return trades


def strat_momo_biased(bars, *, hours=range(7, 20), brk=12, atr_n=14, k_stop=2.0,
                      tp_mult=2.0, hold=48, n_long=240):
    """Intraday momentum: in active hours, break of `brk`-bar high/low ALIGNED with
    higher-TF bias; ATR stop, fixed-R target, time exit."""
    t = [b[0] for b in bars]; o = [b[1] for b in bars]; h = [b[2] for b in bars]
    lo = [b[3] for b in bars]; c = [b[4] for b in bars]
    n = len(c); bias = bias_long_short(c, n_long)
    # ATR (Wilder) on M5
    tr = [h[0] - lo[0]]
    for i in range(1, n):
        tr.append(max(h[i] - lo[i], abs(h[i] - c[i - 1]), abs(lo[i] - c[i - 1])))
    atr = [tr[0]] * n
    for i in range(1, n):
        atr[i] = (atr[i - 1] * (atr_n - 1) + tr[i]) / atr_n if i >= atr_n else sum(tr[:i + 1]) / (i + 1)
    trades = []; i = max(brk, n_long) + 50
    while i < n - 1:
        if t[i].hour not in hours or atr[i] <= 0 or bias[i] == 0:
            i += 1; continue
        hh = max(h[i - brk:i]); ll = min(lo[i - brk:i]); side = None
        if c[i] > hh and bias[i] == 1:
            side = "long"
        elif c[i] < ll and bias[i] == -1:
            side = "short"
        if side is None:
            i += 1; continue
        entry = o[i + 1]; A = atr[i]; stopd = k_stop * A
        tp = entry + tp_mult * stopd if side == "long" else entry - tp_mult * stopd
        j = i + 1; exit_px = None
        while j < n and (j - i) <= hold:
            if side == "long":
                if lo[j] <= entry - stopd:
                    exit_px = entry - stopd; break
                if h[j] >= tp:
                    exit_px = tp; break
            else:
                if h[j] >= entry + stopd:
                    exit_px = entry + stopd; break
                if lo[j] <= tp:
                    exit_px = tp; break
            j += 1
        if exit_px is None:
            exit_px = c[min(j, n - 1)]
        gross = (exit_px - entry) if side == "long" else (entry - exit_px)
        trades.append({"t": t[i], "gross": gross})
        i = j + 1
    return trades


def combine(*trade_lists):
    out = []
    for tl in trade_lists:
        out.extend(tl)
    out.sort(key=lambda x: x["t"])
    return out


if __name__ == "__main__":
    bars = load()
    print(f"loaded {len(bars)} M5 bars\n")
    print(f"{'STRATEGY':<34} {'stats':<70} weekly-consistency")
    print("-" * 130)
    orbB = strat_orb_biased(bars)
    momoB = strat_momo_biased(bars)
    evaluate(orbB, "B+ ORB London+NY (bias-filtered)")
    evaluate(momoB, "D momentum breakout (bias-filt)")
    evaluate(combine(orbB, momoB), "PORTFOLIO B+ & D combined")
