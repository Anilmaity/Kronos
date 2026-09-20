"""Challenge-safe XAUUSD strategy: H4 Donchian trend-follow, risk-sized for a $5k
FundingPips-style challenge (+$500 target, ~5%/10% drawdown limits).

This is the deployable answer to the "5000->5500" research (see
reports/mobile_scalp_research.md). The manual no-stop mobile scalp on account
5216074f reproduces its 92.5% win rate in backtest but ruins a challenge 72.5% of
the time; this trend-follow edge (PF 1.83 on H4, positive every year 2023-2026)
passes ~65-77% of the time when sized so a -1R loss stays inside the daily limit.

Design (zero discretion):
  bias   : EMA20 > EMA50 (long-only) / EMA20 < EMA50 (short-only) on H4 closes
  entry  : close breaks the Donchian(20) high (long) / low (short) in the bias dir
  stop   : 3 x ATR(14) chandelier TRAILING stop (initial hard stop = entry -/+ 3*ATR)
  size   : lot = risk_budget / (3 * ATR * $10-per-point-per-0.1-lot), capped
  exit   : trailing stop only (let winners run -> fat right tail)

Pure + data-driven so it can be unit-tested offline. Live wiring (place via
bot.broker / metaapi REST) is a thin layer on top of `signal()` + `position_size()`.
"""
from __future__ import annotations

USD_PER_POINT_PER_0_1_LOT = 10.0  # 1.0 XAU price point = $10 at 0.10 lot


def ema(vals, n):
    k = 2 / (n + 1)
    out = [vals[0]]
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


def position_size(equity, atr_now, *, risk_pct=0.008, risk_floor=40.0,
                  k_atr=3.0, min_lot=0.01, max_lot=0.50, lot_step=0.01):
    """Lots so that a -1R (k_atr*ATR) move risks ~max(risk_floor, risk_pct*equity)."""
    risk_dollars = max(risk_floor, risk_pct * equity)
    risk_points = k_atr * atr_now
    if risk_points <= 0:
        return 0.0, 0.0
    raw_lot = risk_dollars / (risk_points * (USD_PER_POINT_PER_0_1_LOT / 0.1))
    lot = max(min_lot, min(max_lot, round(raw_lot / lot_step) * lot_step))
    actual_risk = risk_points * (USD_PER_POINT_PER_0_1_LOT / 0.1) * lot
    return round(lot, 2), round(actual_risk, 2)


def signal(o, h, l, c, *, N=20, ema_fast=20, ema_slow=50, k_atr=3.0):
    """Return ('long'|'short'|None, entry_ref, init_stop, atr_now) for the LAST bar."""
    if len(c) < max(N, ema_slow) + 2:
        return None, None, None, None
    ef, es = ema(c, ema_fast), ema(c, ema_slow)
    a = atr(h, l, c, 14)
    i = len(c) - 1
    donch_hi = max(h[i - N:i]); donch_lo = min(l[i - N:i])
    up = ef[i] > es[i]
    A = a[i]
    if A <= 0:
        return None, None, None, A
    if c[i] > donch_hi and up:
        return "long", c[i], c[i] - k_atr * A, A
    if c[i] < donch_lo and not up:
        return "short", c[i], c[i] + k_atr * A, A
    return None, None, None, A


def backtest(bars, *, N=20, k_atr=3.0, spread=0.30, commission=0.50,
             ema_fast=20, ema_slow=50, lot=0.1):
    """bars: list of (t,o,h,l,c). Donchian breakout + chandelier trail. Returns trades."""
    o = [b[1] for b in bars]; h = [b[2] for b in bars]
    l = [b[3] for b in bars]; c = [b[4] for b in bars]; t = [b[0] for b in bars]
    n = len(c)
    ef, es = ema(c, ema_fast), ema(c, ema_slow); a = atr(h, l, c, 14)
    trades = []; i = max(N, ema_slow) + 1
    mult = USD_PER_POINT_PER_0_1_LOT * (lot / 0.1)
    while i < n - 1:
        donch_hi = max(h[i - N:i]); donch_lo = min(l[i - N:i]); up = ef[i] > es[i]
        side = "long" if (c[i] > donch_hi and up) else ("short" if (c[i] < donch_lo and not up) else None)
        if side is None:
            i += 1; continue
        A = a[i]
        if A <= 0:
            i += 1; continue
        entry = o[i + 1] + (spread / 2 if side == "long" else -spread / 2)
        risk = k_atr * A
        j = i + 1; exit_px = None
        if side == "long":
            trail = entry - risk; hh = entry
            while j < n:
                hh = max(hh, h[j]); trail = max(trail, hh - risk)
                if l[j] <= trail:
                    exit_px = trail; break
                j += 1
            if exit_px is None:
                exit_px = c[-1]; j = n - 1
            pts = exit_px - entry
        else:
            trail = entry + risk; ll = entry
            while j < n:
                ll = min(ll, l[j]); trail = min(trail, ll + risk)
                if h[j] >= trail:
                    exit_px = trail; break
                j += 1
            if exit_px is None:
                exit_px = c[-1]; j = n - 1
            pts = entry - exit_px
        trades.append({"t": t[i], "side": side, "R": pts / risk,
                       "pnl": pts * mult - commission})
        i = j + 1
    return trades


def summary(trades):
    if not trades:
        return {"n": 0}
    n = len(trades); wins = [x for x in trades if x["pnl"] > 0]
    net = sum(x["pnl"] for x in trades)
    gl = sum(x["pnl"] for x in trades if x["pnl"] <= 0)
    gw = sum(x["pnl"] for x in wins)
    return {"n": n, "wr": 100 * len(wins) / n, "pf": (gw / abs(gl) if gl else float("inf")),
            "net": net, "exp": net / n, "worst_R": min(x["R"] for x in trades)}
