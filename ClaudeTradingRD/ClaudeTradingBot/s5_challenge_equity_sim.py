"""Challenge-scaled equity curve on CURRENT data.

The backtest()'s net $ are at a FIXED 0.1 lot, which over-risks a $5k account when
gold is ~$4000 (3*ATR*$10 can be $900-1500/trade). The deployable strategy sizes by
RISK via position_size() (~0.8% equity, $40 floor). This sim applies that sizing to the
realized R of each trade to get the TRUE challenge P&L, max drawdown, and pass/fail vs
FundingPips-style limits ($500 target, ~$250 daily / ~$500 overall trailing DD on $5k).
"""
import datetime as dt

from bot import data as D
from bot import challenge_xau as S


def fetch_oanda_h4(count=5000):
    bars = []
    for r in D.candles(granularity="H4", count=count, price="M"):
        if not r["complete"]:
            continue
        t = dt.datetime.strptime(r["time"][:19], "%Y-%m-%dT%H:%M:%S")
        bars.append((t, r["o"], r["h"], r["l"], r["c"]))
    bars.sort(key=lambda b: b[0])
    seen, out = set(), []
    for b in bars:
        if b[0] not in seen:
            seen.add(b[0]); out.append(b)
    return out


def backtest_with_atr(bars, *, N=20, k_atr=3.0, spread=0.30, commission=0.50,
                      ema_fast=20, ema_slow=50):
    """Same logic as S.backtest but records ATR-at-entry so we can risk-size."""
    o = [b[1] for b in bars]; h = [b[2] for b in bars]
    l = [b[3] for b in bars]; c = [b[4] for b in bars]; t = [b[0] for b in bars]
    n = len(c)
    ef, es = S.ema(c, ema_fast), S.ema(c, ema_slow); a = S.atr(h, l, c, 14)
    trades = []; i = max(N, ema_slow) + 1
    while i < n - 1:
        donch_hi = max(h[i - N:i]); donch_lo = min(l[i - N:i]); up = ef[i] > es[i]
        side = "long" if (c[i] > donch_hi and up) else ("short" if (c[i] < donch_lo and not up) else None)
        if side is None:
            i += 1; continue
        A = a[i]
        if A <= 0:
            i += 1; continue
        entry = o[i + 1] + (spread / 2 if side == "long" else -spread / 2)
        risk = k_atr * A; j = i + 1; exit_px = None
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
        trades.append({"t": t[i], "side": side, "R": pts / risk, "atr": A})
        i = j + 1
    return trades


def sim(bars, start=5000.0, target=5500.0, daily_limit=250.0, overall_dd=500.0):
    trades = backtest_with_atr(bars)
    eq = start; peak = start; maxdd = 0.0
    worst_day = 0.0; day = None; day_pnl = 0.0
    curve = []
    hit_target = None; breach = None
    for tr in trades:
        lot, risk_usd = S.position_size(eq, tr["atr"])
        pnl = tr["R"] * risk_usd - 0.50
        eq += pnl
        # daily aggregation (calendar date of entry as proxy)
        d = tr["t"].date()
        if d != day:
            worst_day = min(worst_day, day_pnl); day = d; day_pnl = 0.0
        day_pnl += pnl
        peak = max(peak, eq); maxdd = max(maxdd, peak - eq)
        curve.append((tr["t"], round(eq, 2), tr["R"], round(pnl, 2)))
        if hit_target is None and eq >= target:
            hit_target = (tr["t"], round(eq, 2))
        if breach is None and (peak - eq) > overall_dd:
            breach = (tr["t"], round(eq, 2), round(peak - eq, 2))
    worst_day = min(worst_day, day_pnl)
    return trades, curve, dict(end_eq=round(eq, 2), maxdd=round(maxdd, 2),
                               worst_day=round(worst_day, 2), hit_target=hit_target,
                               breach=breach)


bars = fetch_oanda_h4()
trades, curve, r = sim(bars)
print(f"current H4 data: {len(bars)} bars  {bars[0][0]} -> {bars[-1][0]}")
print(f"trades: {len(trades)}   start $5000 -> end ${r['end_eq']}")
print(f"max drawdown: ${r['maxdd']}   worst single day: ${r['worst_day']}")
print(f"target $5500 first hit: {r['hit_target']}")
print(f"overall-DD ($500) breach: {r['breach']}")

# last 90 days, risk-sized
cut = bars[-1][0] - dt.timedelta(days=90)
recent = [x for x in curve if x[0] >= cut]
if recent:
    base = next((c[1] for c in curve if c[0] >= cut), 5000)
    rsum = sum(x[3] for x in recent)
    print(f"\nlast 90d (risk-sized): {len(recent)} trades, "
          f"sumR={sum(x[2] for x in recent):+.2f}, net=${rsum:+.0f}")
    for x in recent[-8:]:
        print(f"  {x[0]}  R={x[2]:+.2f}  pnl=${x[3]:+.0f}  eq=${x[1]}")

print("\n=== VERDICT (risk-sized, current data) ===")
passed = r["breach"] is None
print(("PASS" if passed else "FAIL") +
      f": maxDD ${r['maxdd']} {'within' if r['maxdd'] <= 500 else 'EXCEEDS'} "
      f"$500 overall limit; worst day ${r['worst_day']} "
      f"{'within' if r['worst_day'] >= -250 else 'EXCEEDS'} $250 daily limit.")
