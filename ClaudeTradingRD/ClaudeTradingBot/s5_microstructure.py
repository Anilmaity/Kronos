"""Characterize XAU 5-second microstructure to see if any fast edge clears the cost floor.

Reads the KronosStrategies S5 JSON cache (4-point synthetic splits of real S5 OHLC).
close-to-close 5s returns are REAL mid-price returns; high/low are synthetic so we use
closes for return stats. Computes: return autocorrelation (mean-reversion vs momentum),
variance ratio, and move-size distribution vs the 0.25pt real spread.
"""
import json, glob, datetime as dt, statistics, math, sys

CACHE = "C:/Projects/PycharmProjects/personal/KronosStrategies/tick_data_collector/Tick_Data_Generator/cache_data/XAU_USD"
SPREAD = 0.25  # real account spread, points


def load_s5_closes(files):
    """Return [(time, close)] from S5 candle groups, gap-aware (per contiguous run)."""
    closes = []
    for fp in files:
        groups = json.load(open(fp, encoding="utf-8"))
        for g in groups:
            t = dt.datetime.fromisoformat(g[0]["time"])
            c = float(g[-1]["price"])
            o = float(g[0]["price"])
            hi = max(float(p["price"]) for p in g)
            lo = min(float(p["price"]) for p in g)
            closes.append((t, o, hi, lo, c))
    closes.sort(key=lambda x: x[0])
    return closes


def returns_5s(bars):
    """Close-to-close diffs in POINTS, skipping gaps > 30s (session breaks)."""
    rs = []
    for i in range(1, len(bars)):
        dtsec = (bars[i][0] - bars[i - 1][0]).total_seconds()
        if dtsec > 30:
            continue
        rs.append(bars[i][4] - bars[i - 1][4])
    return rs


def autocorr(x, lag):
    n = len(x)
    if n <= lag:
        return float("nan")
    m = sum(x) / n
    num = sum((x[i] - m) * (x[i - lag] - m) for i in range(lag, n))
    den = sum((v - m) ** 2 for v in x)
    return num / den if den else float("nan")


def variance_ratio(x, q):
    """VR(q) = Var(sum of q returns)/(q*Var(1)). <1 mean-revert, >1 trend, =1 random."""
    n = len(x)
    if n < q + 2:
        return float("nan")
    mu = sum(x) / n
    var1 = sum((v - mu) ** 2 for v in x) / (n - 1)
    if var1 == 0:
        return float("nan")
    agg = [sum(x[i:i + q]) for i in range(0, n - q + 1)]
    mq = sum(agg) / len(agg)
    varq = sum((v - mq) ** 2 for v in agg) / (len(agg) - 1)
    return varq / (q * var1)


if __name__ == "__main__":
    files = sorted(glob.glob(CACHE + "/*.json"))
    print(f"Loaded cache files: {len(files)}")
    bars = load_s5_closes(files)
    print(f"S5 bars: {len(bars)}  {bars[0][0]} .. {bars[-1][0]}")
    rs = returns_5s(bars)
    n = len(rs)
    absr = [abs(r) for r in rs]
    print(f"\n5s close-to-close returns: n={n}")
    print(f"  mean abs move: {statistics.mean(absr):.4f} pt   median: {statistics.median(absr):.4f} pt")
    print(f"  std: {statistics.pstdev(rs):.4f} pt   max abs: {max(absr):.3f} pt")
    print(f"  spread = {SPREAD} pt -> fraction of 5s moves that even EXCEED the spread: "
          f"{100*sum(1 for a in absr if a > SPREAD)/n:.1f}%")
    zero = sum(1 for a in absr if a == 0)
    print(f"  fraction of 5s bars with ZERO move: {100*zero/n:.1f}%")

    print("\n--- Return autocorrelation (negative = mean-reverting / fade-able) ---")
    for lag in (1, 2, 3, 6, 12):
        print(f"  lag {lag*5:3d}s: AC = {autocorr(rs, lag):+.4f}")

    print("\n--- Variance ratio (q x 5s); <1 mean-revert, >1 trend ---")
    for q in (2, 6, 12, 60, 240):
        print(f"  q={q:3d} ({q*5:4d}s): VR = {variance_ratio(rs, q):.3f}")

    # Move-size over longer horizons vs spread: can a scalp capture > spread+cost?
    print("\n--- N-second forward move size vs spread (can a TP clear costs?) ---")
    closes = [b[4] for b in bars]
    times = [b[0] for b in bars]
    for horizon_s in (15, 30, 60, 120, 300):
        k = horizon_s // 5
        moves = []
        for i in range(len(closes) - k):
            if (times[i + k] - times[i]).total_seconds() <= horizon_s + 30:
                moves.append(abs(closes[i + k] - closes[i]))
        if moves:
            med = statistics.median(moves)
            p75 = sorted(moves)[int(len(moves) * .75)]
            frac = 100 * sum(1 for m in moves if m > SPREAD + 0.05) / len(moves)
            print(f"  {horizon_s:3d}s: median |move| {med:.3f}pt  p75 {p75:.3f}pt  "
                  f"% > spread+cost: {frac:.0f}%")
