"""Backtest: does 'sell the bounce in a XAUUSD daily downtrend' have an edge?

Zero-discretion systematic rules tested over the full OANDA XAU_USD daily history,
with friction. Goal is to learn gold's character (momentum vs mean-reversion) and
whether the trade I'm resting (short rallies into supply in a downtrend) is real.

    .venv/Scripts/python.exe bt_xau_trend.py
"""
import statistics as st
from bot import data

COST = 1.0   # round-trip cost in $ (spread+slippage), conservative for gold
COST_2X = 2.0


def ema(vals, n):
    k = 2 / (n + 1)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(closes, n=2):
    out = [50.0] * len(closes)
    gains, losses = [], []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0)); losses.append(max(-ch, 0))
        if i >= n:
            ag = sum(gains[-n:]) / n; al = sum(losses[-n:]) / n
            out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def summarize(name, rets, cost):
    """rets = list of per-trade % returns (already directional, before cost)."""
    net = [r - cost_pct for r, cost_pct in ((r, 100 * cost / 4000.0) for r in rets)]
    if not net:
        print(f"{name}: no trades"); return
    wins = [r for r in net if r > 0]
    exp = sum(net) / len(net)
    pf = (sum(wins) / -sum(r for r in net if r < 0)) if any(r < 0 for r in net) else float('inf')
    print(f"{name}: n={len(net):4d}  win%={100*len(wins)/len(net):5.1f}  "
          f"exp/trade={exp:+.3f}%  total={sum(net):+.1f}%  PF={pf:.2f}  "
          f"avgW={st.mean(wins) if wins else 0:+.2f} avgL={st.mean([r for r in net if r<=0]) if any(r<=0 for r in net) else 0:+.2f}")
    return net


def by_year(name, dates, net):
    yrs = {}
    for d, r in zip(dates, net):
        yrs.setdefault(d[:4], []).append(r)
    line = "  ".join(f"{y}:{sum(v):+.0f}%({len(v)})" for y, v in sorted(yrs.items()))
    print(f"   {name} by year: {line}")


def main():
    cs = data.candles(granularity="D", count=2000)
    cs = [c for c in cs if c["complete"]]
    o = [c["o"] for c in cs]; h = [c["h"] for c in cs]
    l = [c["l"] for c in cs]; c_ = [c["c"] for c in cs]
    t = [c["time"][:10] for c in cs]
    n = len(cs)
    print(f"XAU_USD daily candles: {n}  from {t[0]} to {t[-1]}  "
          f"(last close {c_[-1]:.2f})\n")

    e20, e50 = ema(c_, 20), ema(c_, 50)
    r2 = rsi(c_, 2)

    # Baseline character checks (no cost): next-day return conditioned on regime/prior day.
    # Entry at day i open, exit at day i close (1-day hold). Short = -(close-open)/open.
    def trade_ret_short(i):  # % return of a 1-day short entered at open[i]
        return -100 * (c_[i] - o[i]) / o[i]

    def trade_ret_long(i):
        return 100 * (c_[i] - o[i]) / o[i]

    downtrend = [e20[i] < e50[i] for i in range(n)]

    # Rule A — momentum continuation short: downtrend AND prior day closed DOWN -> short today.
    A = [(t[i], trade_ret_short(i)) for i in range(50, n)
         if downtrend[i - 1] and c_[i - 1] < o[i - 1]]
    # Rule B — mean-reversion short (THE trade): downtrend AND prior day closed UP (bounce) -> short today.
    B = [(t[i], trade_ret_short(i)) for i in range(50, n)
         if downtrend[i - 1] and c_[i - 1] > o[i - 1]]
    # Rule C — RSI(2) overbought bounce in downtrend -> short today, 1-day hold.
    C = [(t[i], trade_ret_short(i)) for i in range(50, n)
         if downtrend[i - 1] and r2[i - 1] > 80]
    # Rule D — control: long the dip in downtrend (prior day down) -> is mean-reversion symmetric?
    D = [(t[i], trade_ret_long(i)) for i in range(50, n)
         if downtrend[i - 1] and c_[i - 1] < o[i - 1]]

    for label, rule, fn in [
        ("A momentum-short (sell weakness, down-trend)", A, trade_ret_short),
        ("B meanrev-short (SELL THE BOUNCE, down-trend)", B, trade_ret_short),
        ("C RSI2>80 short (down-trend)", C, trade_ret_short),
        ("D control long-the-dip (down-trend)", D, trade_ret_long),
    ]:
        dates = [d for d, _ in rule]; rets = [r for _, r in rule]
        net = summarize(label, rets, COST)
        if net:
            by_year(label.split()[0], dates, net)
        net2 = summarize(label + " [2x cost]", rets, COST_2X)
        print()


if __name__ == "__main__":
    main()
