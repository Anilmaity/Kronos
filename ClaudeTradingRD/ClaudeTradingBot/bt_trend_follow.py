"""Backtest #4: TREND-FOLLOWING on XAUUSD — the hypothesis the prior 3 tests point to.

All reversal/mean-reversion daily rules failed; the only positive years were strong
TREND years (2022, 2026), and the HTF bias filter always helped. So test the natural
alternative: Donchian breakout entries in the bias direction, ridden with an ATR
(chandelier) trailing stop. Trend-following wins via fat right tails, so judge it on
total R and PF, not win rate (low WR is normal and fine).

    .venv/Scripts/python.exe bt_trend_follow.py
"""
from bot import data

COST = 1.0


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


def run(o, h, l, c, t, e20, e50, a, N, k):
    """Donchian(N) breakout in bias dir, chandelier(k*ATR) trailing exit. One position at a time."""
    n = len(c); trades = []; i = N + 50
    while i < n - 1:
        donch_hi = max(h[i - N:i]); donch_lo = min(l[i - N:i])
        up = e20[i] > e50[i]
        side = None
        if c[i] > donch_hi and up:
            side = "long"
        elif c[i] < donch_lo and not up:
            side = "short"
        if side is None:
            i += 1; continue
        entry = o[i + 1]; A = a[i]
        if A <= 0:
            i += 1; continue
        risk = k * A
        if side == "long":
            trail = entry - risk; hh = entry
            j = i + 1; exit_px = None
            while j < n:
                hh = max(hh, h[j]); trail = max(trail, hh - risk)
                if l[j] <= trail:
                    exit_px = trail; break
                j += 1
            if exit_px is None:
                exit_px = c[-1]; j = n - 1
            R = (exit_px - entry) / risk
        else:
            trail = entry + risk; ll = entry
            j = i + 1; exit_px = None
            while j < n:
                ll = min(ll, l[j]); trail = min(trail, ll + risk)
                if h[j] >= trail:
                    exit_px = trail; break
                j += 1
            if exit_px is None:
                exit_px = c[-1]; j = n - 1
            R = (entry - exit_px) / risk
        trades.append((t[i], side, R - COST / risk))
        i = j + 1  # no overlapping positions
    return trades


def report(label, tr):
    if not tr:
        print(f"{label}: no trades"); return
    rs = [r for _, _, r in tr]; wins = [r for r in rs if r > 0]
    pf = sum(wins) / -sum(r for r in rs if r < 0) if any(r < 0 for r in rs) else float("inf")
    print(f"{label}: n={len(rs)}  WR={100*len(wins)/len(rs):.0f}%  PF={pf:.2f}  "
          f"expR={sum(rs)/len(rs):+.3f}  totR={sum(rs):+.1f}  "
          f"bestR={max(rs):+.1f} worstR={min(rs):+.1f}")
    yrs = {}
    for d, _, r in tr:
        yrs.setdefault(d[:4], []).append(r)
    print("   by year R: " + "  ".join(f"{y}:{sum(v):+.1f}({len(v)})" for y, v in sorted(yrs.items())))


def main():
    cs = [x for x in data.candles(granularity="D", count=2000) if x["complete"]]
    o = [x["o"] for x in cs]; h = [x["h"] for x in cs]
    l = [x["l"] for x in cs]; c = [x["c"] for x in cs]; t = [x["time"][:10] for x in cs]
    e20, e50 = ema(c, 20), ema(c, 50); a = atr(h, l, c, 14)
    print(f"XAU_USD daily: {len(cs)} bars {t[0]}..{t[-1]}  last {c[-1]:.2f}")
    print("Donchian breakout in EMA20/50 bias dir, chandelier ATR trailing stop.\n")
    for N in (20, 40, 55):
        for k in (2.0, 3.0):
            report(f"Donchian({N}) trail {k}xATR", run(o, h, l, c, t, e20, e50, a, N, k))
        print()


if __name__ == "__main__":
    main()
