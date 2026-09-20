"""HighWR-TrendPullback — the closest HONEST reproduction of the live account's
high-win-rate + profit, built as a real system (see reports/mobile_scalp_research.md).

The live account's 92.5% WR was a no-stop illusion (random entries reproduce 86%);
it had near-zero true expectancy and a ruin tail. This system instead targets a
GENUINE, out-of-sample-validated high win rate (~70-74%) that actually profits, by
trading WITH the higher-timeframe trend and taking a small profit on pullback entries:

  bias   : EMA(fast) vs EMA(slow) on the trading TF (long-only in uptrend, short-only down)
  entry  : price pulls back to ~the fast EMA but holds above/below the slow EMA
           (a healthy trend pullback, not a breakdown)
  exit   : small fixed take-profit (tp_atr * ATR) -> the source of the high win rate
           hard stop (sl_atr * ATR) -> caps the tail the live account lacked
           time stop (max_hold bars)

Validated on XAU H4 2023-2026 (train/test split, swap included): ~74% WR, PF ~1.06,
positive in 3 of 4 years. HONEST caveats: the edge is THIN and TREND-REGIME-DEPENDENT
(it can have a losing year in choppy/reversing markets) and gold SWAP on long holds
erodes it. It is NOT a robust every-year money machine — it is the highest win rate at
which the profit is real rather than luck. For maximum robustness (lower WR ~49% but
sturdier PF 1.6-1.8) use bot/challenge_xau.py instead. This module is for the user who
specifically wants the high-win-rate feel with profit that survives out-of-sample.
"""
from __future__ import annotations

USD_PER_POINT_PER_0_1_LOT = 10.0


def ema(vals, n):
    k = 2 / (n + 1); out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def atr(h, l, c, n=14):
    trs = [h[0] - l[0]]
    for i in range(1, len(c)):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    out = [trs[0]] * len(c)
    for i in range(1, len(c)):
        out[i] = (out[i - 1] * (n - 1) + trs[i]) / n if i >= n else sum(trs[:i + 1]) / (i + 1)
    return out


def position_size(equity, *, stop_points, risk_pct=0.006, risk_floor=30.0,
                  min_lot=0.01, max_lot=0.50, lot_step=0.01):
    risk_dollars = max(risk_floor, risk_pct * equity)
    if stop_points <= 0:
        return 0.0, 0.0
    raw = risk_dollars / (stop_points * (USD_PER_POINT_PER_0_1_LOT / 0.1))
    lot = max(min_lot, min(max_lot, round(raw / lot_step) * lot_step))
    return round(lot, 2), round(stop_points * (USD_PER_POINT_PER_0_1_LOT / 0.1) * lot, 2)


def signal(closes, highs, lows, *, ema_fast=10, ema_slow=50, tp_atr=0.8, sl_atr=2.0,
           band_atr=0.2):
    """Return (side, tp_points, sl_points) or (None, ..). closes/highs/lows newest last.
    Uptrend pullback -> long; downtrend pullback -> short."""
    n = len(closes)
    if n < ema_slow + 2:
        return None, None, None
    ef = ema(closes, ema_fast); es = ema(closes, ema_slow)
    a = atr(highs, lows, closes, 14)
    i = n - 1; A = a[i]
    if A <= 0:
        return None, None, None
    up = ef[i] > es[i]
    c = closes[i]
    if up and (c <= ef[i] + band_atr * A) and (c >= es[i]):
        return "long", tp_atr * A, sl_atr * A
    if (not up) and (c >= ef[i] - band_atr * A) and (c <= es[i]):
        return "short", tp_atr * A, sl_atr * A
    return None, None, None
