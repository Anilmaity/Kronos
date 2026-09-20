"""Backtest #2: does ASYMMETRIC R:R + a trend filter rescue the coin-flip direction?

The 1-day-hold test (bt_xau_trend.py) showed no directional edge. But my live trade
is a level-to-level short at ~2.7:1. This tests trend-filtered shorts with an ATR stop
and a fixed-R target, simulated forward bar-by-bar until stop/target/time-exit, with
friction and a parameter sweep (seek plateaus, not peaks).

    .venv/Scripts/python.exe bt_xau_rr.py
"""
from bot import data

COST = 1.0   # round-trip $; ATR-normalized below


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


def rsi(closes, n=2):
    out = [50.0] * len(closes); g = []; ls = []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]; g.append(max(ch, 0)); ls.append(max(-ch, 0))
        if i >= n:
            ag = sum(g[-n:]) / n; al = sum(ls[-n:]) / n
            out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def main():
    cs = [c for c in data.candles(granularity="D", count=2000) if c["complete"]]
    o = [c["o"] for c in cs]; h = [c["h"] for c in cs]
    l = [c["l"] for c in cs]; c_ = [c["c"] for c in cs]; t = [c["time"][:10] for c in cs]
    n = len(cs)
    e20, e50 = ema(c_, 20), ema(c_, 50); a = atr(h, l, c_, 14); r2 = rsi(c_, 2)
    print(f"XAU_USD daily: {n} bars {t[0]}..{t[-1]}  last {c_[-1]:.2f}\n")

    T = 12  # time-stop in days

    def run(stop_mult, tgt_mult, signal):
        trades = []  # (date, R_result)
        for i in range(50, n - 1):
            down = e20[i - 1] < e50[i - 1]
            if not (down and signal(i)):
                continue
            entry = o[i]; A = a[i - 1]
            if A <= 0:
                continue
            stop = entry + stop_mult * A      # short -> stop above
            tgt = entry - tgt_mult * A        # target below
            cost_R = COST / (stop_mult * A)   # cost expressed in R
            res = None
            for j in range(i, min(i + T, n)):
                if h[j] >= stop:              # stop first if both hit same bar (conservative)
                    res = -1.0; break
                if l[j] <= tgt:
                    res = tgt_mult / stop_mult; break
            if res is None:                   # time exit at close
                res = (entry - c_[min(i + T - 1, n - 1)]) / (stop_mult * A)
            trades.append((t[i], res - cost_R))
        return trades

    sig_up = lambda i: c_[i - 1] > o[i - 1]          # bounce = prior up day
    sig_rsi = lambda i: r2[i - 1] > 80               # overbought bounce

    print("Trend-filtered SHORT, ATR stop, fixed-R target, time-stop 12d, cost modeled.")
    print("Expectancy in R (risk units). Edge if exp/trade > 0 and stable across the grid.\n")
    for name, sig in [("bounce=prior-up-day", sig_up), ("bounce=RSI2>80", sig_rsi)]:
        print(f"--- signal: {name} ---")
        print(f"{'stopxATR':>8} {'tgtxATR':>7} {'n':>4} {'win%':>6} {'expR':>7} {'totR':>7}")
        for sm in (1.0, 1.5, 2.0):
            for tm in (1.5, 2.0, 3.0):
                tr = run(sm, tm, sig)
                if not tr:
                    continue
                rs = [r for _, r in tr]
                wins = sum(1 for r in rs if r > 0)
                exp = sum(rs) / len(rs)
                print(f"{sm:>8.1f} {tm:>7.1f} {len(rs):>4} {100*wins/len(rs):>5.1f}% "
                      f"{exp:>+7.3f} {sum(rs):>+7.1f}")
        # by-year for the central cell (1.5 stop, 2.0 tgt)
        tr = run(1.5, 2.0, sig); yrs = {}
        for d, r in tr:
            yrs.setdefault(d[:4], []).append(r)
        print("   central(1.5/2.0) by year R: " +
              "  ".join(f"{y}:{sum(v):+.1f}({len(v)})" for y, v in sorted(yrs.items())))
        print()


if __name__ == "__main__":
    main()
