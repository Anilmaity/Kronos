"""(A) Does trend-aligning the scalp rescue it?  (B) What do averaging + 100x do to it?

Run after bt_scalp.py. Honest quantification of the requested approach.
    .venv/Scripts/python.exe bt_scalp_risk.py
"""
from bot import data


def ema(v, n):
    k = 2 / (n + 1); out = [v[0]]
    for x in v[1:]:
        out.append(x * k + out[-1] * (1 - k))
    return out


def main():
    cs = [c for c in data.candles(granularity="M15", count=5000) if c["complete"]]
    o = [c["o"] for c in cs]; h = [c["h"] for c in cs]
    l = [c["l"] for c in cs]; c_ = [c["c"] for c in cs]
    n = len(cs); N = 50
    e50, e200 = ema(c_, 50), ema(c_, 200)
    z = [0.0] * n
    for i in range(N, n):
        w = c_[i - N + 1:i + 1]; m = sum(w) / N
        sd = (sum((x - m) ** 2 for x in w) / N) ** 0.5
        z[i] = (c_[i] - m) / sd if sd > 0 else 0.0

    # ---------- (A) trend-filtered scalp: only fade WITH the M15 trend ----------
    def bt(tp, sl, with_trend, cost=0.30):
        tr = []; i = N + 1
        while i < n - 1:
            up = e50[i] > e200[i]
            side = None
            if z[i] <= -2.0:           # dip -> long (mean reversion)
                side = "long"
            elif z[i] >= 2.0:          # rip -> short
                side = "short"
            if side is None:
                i += 1; continue
            if with_trend:             # only longs in uptrend, shorts in downtrend
                if (side == "long" and not up) or (side == "short" and up):
                    i += 1; continue
            entry = o[i + 1]
            tp_px = entry + tp if side == "long" else entry - tp
            sl_px = entry - sl if side == "long" else entry + sl
            res = None
            for j in range(i + 1, n):
                if side == "long":
                    if l[j] <= sl_px: res = -sl; break
                    if h[j] >= tp_px: res = tp; break
                else:
                    if h[j] >= sl_px: res = -sl; break
                    if l[j] <= tp_px: res = tp; break
            if res is None: res = 0; j = n - 1
            tr.append(res - cost); i = j + 1
        return tr

    print("(A) Trend-aligned scalp (only fade with the M15 EMA50/200 trend), TP3/SL9:")
    for wt in (False, True):
        tr = bt(3, 9, wt)
        wins = [x for x in tr if x > 0]
        pf = sum(wins) / -sum(x for x in tr if x < 0) if any(x < 0 for x in tr) else 9.99
        lab = "with-trend" if wt else "no-filter "
        print(f"   {lab}: n={len(tr)} WR={100*len(wins)/len(tr):.0f}% "
              f"exp${sum(tr)/len(tr):+.3f} PF={pf:.2f} total${sum(tr):+.1f}")

    # ---------- (B) martingale averaging + 100x leverage ruin sim ----------
    # Real M15 path. Open 0.01 long-the-dip; if price falls G$, DOUBLE (martingale)
    # to lower breakeven; close the whole basket at +tp$ net or when it reverts.
    # Account $5000, 100x leverage. Track worst drawdown and ruin.
    print("\n(B) Martingale 'averaging to recover' on the same scalp, $5000 @ 100x:")
    for G, tp, max_adds in [(5, 3, 6), (8, 4, 6), (10, 5, 8)]:
        equity = 5000.0; ruin = False; worst_dd = 0.0; baskets = 0; blown_at = None
        i = N + 1
        while i < n - 1:
            if z[i] > -2.0:
                i += 1; continue
            baskets += 1
            base_entry = o[i + 1]
            lots = [(0.01, base_entry)]  # (lot, price)
            j = i + 1
            while j < n:
                price = c_[j]
                tot_lot = sum(L for L, _ in lots)
                avg = sum(L * P for L, P in lots) / tot_lot
                # floating PnL ($1 per $1 per 0.01 lot)
                fpnl = (price - avg) * tot_lot * 100
                dd = -fpnl
                worst_dd = max(worst_dd, dd)
                if equity + fpnl <= 0:           # margin call / ruin
                    ruin = True; blown_at = cs[j]["time"][:16]; break
                if price >= avg + tp:            # basket closes in profit
                    equity += fpnl; break
                # add (double) every G$ of further adverse move beyond last add
                last_add = lots[-1][1]
                if price <= last_add - G and len(lots) <= max_adds:
                    lots.append((lots[-1][0] * 2, price))
                j += 1
            if ruin:
                break
            i = j + 1
        status = (f"RUIN at {blown_at}" if ruin else f"survived, end ${equity:,.0f}")
        print(f"   add-every ${G}, tp ${tp}, max {max_adds} adds: "
              f"{baskets} baskets, worst floating DD ${worst_dd:,.0f} -> {status}")


if __name__ == "__main__":
    main()
