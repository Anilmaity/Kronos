"""Technical analysis for XAUUSD: trend, structure, ATR, key levels, FVGs."""
from datetime import datetime, timezone, timedelta


def ema(values, period):
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    out = [sum(values[:period]) / period]
    for v in values[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def atr(candles, period=14):
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["h"], candles[i]["l"], candles[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return None
    a = sum(trs[:period]) / period
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
    return round(a, 2)


def swings(candles, lookback=2):
    """Fractal swing highs/lows: bar higher/lower than `lookback` bars each side."""
    highs, lows = [], []
    for i in range(lookback, len(candles) - lookback):
        win = candles[i - lookback:i + lookback + 1]
        if candles[i]["h"] == max(c["h"] for c in win):
            highs.append({"i": i, "time": candles[i]["time"], "price": candles[i]["h"]})
        if candles[i]["l"] == min(c["l"] for c in win):
            lows.append({"i": i, "time": candles[i]["time"], "price": candles[i]["l"]})
    return highs, lows


def structure_bias(candles):
    """HH/HL vs LH/LL on the last few swings -> 'bullish' | 'bearish' | 'ranging'."""
    highs, lows = swings(candles)
    if len(highs) < 2 or len(lows) < 2:
        return "ranging"
    hh = highs[-1]["price"] > highs[-2]["price"]
    hl = lows[-1]["price"] > lows[-2]["price"]
    if hh and hl:
        return "bullish"
    if (not hh) and (not hl):
        return "bearish"
    return "ranging"


def fair_value_gaps(candles, min_size=0.0):
    """3-candle FVGs. Bullish: c1.h < c3.l. Bearish: c1.l > c3.h."""
    gaps = []
    for i in range(2, len(candles)):
        c1, c3 = candles[i - 2], candles[i]
        if c3["l"] > c1["h"] and (c3["l"] - c1["h"]) >= min_size:
            gaps.append({"type": "bullish", "top": c3["l"], "bottom": c1["h"],
                         "time": candles[i - 1]["time"]})
        if c1["l"] > c3["h"] and (c1["l"] - c3["h"]) >= min_size:
            gaps.append({"type": "bearish", "top": c1["l"], "bottom": c3["h"],
                         "time": candles[i - 1]["time"]})
    return gaps


def unfilled_gaps(candles, gaps, current_price):
    """Keep gaps not yet fully traded through after formation, near price."""
    out = []
    for g in gaps:
        filled = False
        for c in candles:
            if c["time"] <= g["time"]:
                continue
            if g["type"] == "bullish" and c["l"] <= g["bottom"]:
                filled = True
                break
            if g["type"] == "bearish" and c["h"] >= g["top"]:
                filled = True
                break
        if not filled:
            mid = (g["top"] + g["bottom"]) / 2
            g["dist"] = round(abs(current_price - mid), 2)
            out.append(g)
    return out


def day_bounds(candles_h1, days_ago=1):
    """Prior-day high/low from H1 UTC candles."""
    days = {}
    for c in candles_h1:
        d = c["time"][:10]
        days.setdefault(d, []).append(c)
    keys = sorted(days)
    if len(keys) <= days_ago:
        return None
    target = days[keys[-1 - days_ago]]
    return {"date": keys[-1 - days_ago],
            "high": max(c["h"] for c in target),
            "low": min(c["l"] for c in target)}


def summarize(tf_name, candles):
    closes = [c["c"] for c in candles]
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    highs, lows = swings(candles)
    return {
        "tf": tf_name,
        "close": closes[-1],
        "bias": structure_bias(candles),
        "ema20": round(e20[-1], 2) if e20 else None,
        "ema50": round(e50[-1], 2) if e50 else None,
        "ema_trend": ("up" if e20 and e50 and e20[-1] > e50[-1] else
                      "down" if e20 and e50 else None),
        "atr": atr(candles),
        "last_swing_high": highs[-1]["price"] if highs else None,
        "last_swing_low": lows[-1]["price"] if lows else None,
        "range_20": (round(max(c["h"] for c in candles[-20:]), 2),
                     round(min(c["l"] for c in candles[-20:]), 2)),
    }
