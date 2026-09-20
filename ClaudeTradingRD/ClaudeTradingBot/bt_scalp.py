"""Scalping backtest: high-WR mean-reversion scalp on XAUUSD M15, + the honest tail.

Entry = z-score mean reversion (z=(c-SMA50)/std50 crosses +/-2). Exit = fixed $ TP/SL
(scalp geometry). Sweeps TP/SL to show the WR<->expectancy tradeoff and the negative-skew
tail (max losing streak, worst trade) that makes averaging+leverage dangerous. Costs modeled.

    .venv/Scripts/python.exe bt_scalp.py
"""
from bot import data
import statistics as st

CONTRACT = 100.0  # 1 lot = 100 oz; $1 move = $100/lot, so 0.01 lot = $1 per $1 move


def sma(v, n, i):
    return sum(v[i - n + 1:i + 1]) / n


def main():
    cs = [c for c in data.candles(granularity="M15", count=5000) if c["complete"]]
    o = [c["o"] for c in cs]; h = [c["h"] for c in cs]
    l = [c["l"] for c in cs]; c_ = [c["c"] for c in cs]; t = [c["time"] for c in cs]
    n = len(cs); N = 50
    days = (n * 15) / (60 * 24)
    print(f"XAU_USD M15: {n} bars ~{days:.0f} days, {t[0][:10]}..{t[-1][:10]}\n")

    # z-score series
    z = [0.0] * n
    for i in range(N, n):
        w = c_[i - N + 1:i + 1]; m = sum(w) / N
        sd = (sum((x - m) ** 2 for x in w) / N) ** 0.5
        z[i] = (c_[i] - m) / sd if sd > 0 else 0.0

    def backtest(tp, sl, entry_z, cost):
        trades = []; i = N + 1
        while i < n - 1:
            side = None
            if z[i] <= -entry_z:
                side = "long"
            elif z[i] >= entry_z:
                side = "short"
            if side is None:
                i += 1; continue
            entry = o[i + 1]
            if side == "long":
                tp_px, sl_px = entry + tp, entry - sl
            else:
                tp_px, sl_px = entry - tp, entry + sl
            res = None
            for j in range(i + 1, n):
                if side == "long":
                    if l[j] <= sl_px:
                        res = -sl; break
                    if h[j] >= tp_px:
                        res = tp; break
                else:
                    if h[j] >= sl_px:
                        res = -sl; break
                    if l[j] <= tp_px:
                        res = tp; break
            if res is None:
                res = (c_[-1] - entry) if side == "long" else (entry - c_[-1]); j = n - 1
            trades.append(res - cost)  # $ per 0.01 lot ($1 per $1 move)
            i = j + 1
        return trades

    print(f"{'TP$':>4} {'SL$':>4} {'n':>4} {'WR%':>5} {'exp$/0.01':>9} {'PF':>5} "
          f"{'maxLoseStreak':>13} {'worst$':>7}  (cost $0.30 RT/0.01lot)")
    for tp, sl in [(2, 4), (2, 6), (3, 6), (3, 9), (5, 8), (5, 12), (4, 4), (6, 6)]:
        tr = backtest(tp, sl, 2.0, 0.30)
        if not tr:
            continue
        wins = [x for x in tr if x > 0]
        pf = sum(wins) / -sum(x for x in tr if x < 0) if any(x < 0 for x in tr) else float("inf")
        # max losing streak
        streak = mx = 0
        for x in tr:
            if x < 0:
                streak += 1; mx = max(mx, streak)
            else:
                streak = 0
        print(f"{tp:>4} {sl:>4} {len(tr):>4} {100*len(wins)/len(tr):>4.0f}% "
              f"{sum(tr)/len(tr):>+9.3f} {pf:>5.2f} {mx:>13} {min(tr):>+7.2f}")


if __name__ == "__main__":
    main()
