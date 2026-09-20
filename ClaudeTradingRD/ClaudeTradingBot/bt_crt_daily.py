"""Backtest #3: validate DAILY CRT on XAUUSD over the full OANDA history.

Daily CRT (AMD): D1=prior day, D2=signal day, D3=entry day.
  Sweep-up -> SHORT: D2.high > D1.high + 0.05*ATR AND D2.close < D1.high.
  Sweep-down -> LONG: mirror.
  Entry = D3 open (next bar). Stop = D2 extreme +/- 0.1*ATR. Target = D1 opposite extreme.
The skill's 6-month sample showed WR60/PF1.63/exp0.25R on 25 trades. Here we test it on
~8 years (~2000 bars) with friction, by year, and with an HTF bias filter (EMA20 vs EMA50),
since the skill warns pure mechanical CRT is the flagged failure mode.

    .venv/Scripts/python.exe bt_crt_daily.py
"""
from bot import data

COST = 1.0  # round-trip $; converted to R per trade via risk distance


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


def simulate(o, h, l, c, t, e20, e50, a, T, bias_filter):
    trades = []
    n = len(c)
    for i in range(50, n - 1):
        A = a[i - 1]
        if A <= 0:
            continue
        d1h, d1l = h[i - 1], l[i - 1]
        setup = None  # ('short'/'long', entry, stop, target)
        # Sweep up -> short
        if h[i] > d1h + 0.05 * A and c[i] < d1h:
            entry = o[i + 1]; stop = h[i] + 0.1 * A; tgt = d1l
            if stop > entry and tgt < entry:
                setup = ("short", entry, stop, tgt)
        # Sweep down -> long
        elif l[i] < d1l - 0.05 * A and c[i] > d1l:
            entry = o[i + 1]; stop = l[i] - 0.1 * A; tgt = d1h
            if stop < entry and tgt > entry:
                setup = ("long", entry, stop, tgt)
        if not setup:
            continue
        side, entry, stop, tgt = setup
        if bias_filter:
            up = e20[i] > e50[i]
            if side == "short" and up:    # only short in down-bias
                continue
            if side == "long" and not up:  # only long in up-bias
                continue
        risk = abs(stop - entry)
        if risk <= 0:
            continue
        rr = abs(entry - tgt) / risk
        cost_R = COST / risk
        res = None
        for j in range(i + 1, min(i + 1 + T, n)):
            if side == "short":
                if h[j] >= stop:
                    res = -1.0; break
                if l[j] <= tgt:
                    res = rr; break
            else:
                if l[j] <= stop:
                    res = -1.0; break
                if h[j] >= tgt:
                    res = rr; break
        if res is None:  # time exit at close of last allowed bar
            last = c[min(i + T, n - 1)]
            res = ((entry - last) if side == "short" else (last - entry)) / risk
        trades.append((t[i], side, res - cost_R, rr))
    return trades


def report(label, tr):
    if not tr:
        print(f"{label}: no trades"); return
    rs = [r for _, _, r, _ in tr]
    wins = [r for r in rs if r > 0]
    exp = sum(rs) / len(rs)
    pf = sum(wins) / -sum(r for r in rs if r < 0) if any(r < 0 for r in rs) else float("inf")
    shorts = sum(1 for _, s, _, _ in tr if s == "short")
    print(f"{label}: n={len(rs)} ({shorts}S/{len(rs)-shorts}L)  WR={100*len(wins)/len(rs):.1f}%  "
          f"PF={pf:.2f}  expR={exp:+.3f}  totR={sum(rs):+.1f}  avgRR={sum(r for _,_,_,r in tr)/len(tr):.2f}")
    yrs = {}
    for d, _, r, _ in tr:
        yrs.setdefault(d[:4], []).append(r)
    print("   by year R: " + "  ".join(f"{y}:{sum(v):+.1f}({len(v)})" for y, v in sorted(yrs.items())))


def main():
    cs = [x for x in data.candles(granularity="D", count=2000) if x["complete"]]
    o = [x["o"] for x in cs]; h = [x["h"] for x in cs]
    l = [x["l"] for x in cs]; c = [x["c"] for x in cs]; t = [x["time"][:10] for x in cs]
    e20, e50 = ema(c, 20), ema(c, 50); a = atr(h, l, c, 14)
    print(f"XAU_USD daily: {len(cs)} bars {t[0]}..{t[-1]}  last {c[-1]:.2f}\n")
    for T in (3, 5):
        print(f"=== time-stop {T} days ===")
        report(f"Daily CRT (no filter)   T={T}", simulate(o, h, l, c, t, e20, e50, a, T, False))
        report(f"Daily CRT (HTF bias gate)T={T}", simulate(o, h, l, c, t, e20, e50, a, T, True))
        print()


if __name__ == "__main__":
    main()
