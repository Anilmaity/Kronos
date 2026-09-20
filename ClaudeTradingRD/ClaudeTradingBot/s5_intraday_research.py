"""DEEP RESEARCH: can an XAUUSD intraday strategy take 2-5 trades/day and be
profitable with HIGH WEEKLY CONSISTENCY on a TAKER-only account?

Headline metric = % of GREEN WEEKS (not net P&L). Taker cost punished:
0.35pt round-trip baseline (0.30 spread + $0.50 comm @0.1lot), 0.45pt pessimistic.
All P&L in instrument points; $ at 0.1 lot = pts * $10. Read-only; no trades.

Candidate families (each tuned to ~2-5 trades/day):
  A. Hour-gated mean-reversion z-fade (MR window 03-09 UTC, per prior research)
  B. London + NY opening-range breakout
  C. Always-on z-fade (no hour gate) -- control, expect frequency-wall failure
"""
import csv
import datetime as dt
import statistics as st

DATA = "reports/xau_m5_3y.csv"
COST_PT = 0.35          # baseline taker round-trip (points)
USD_PER_PT = 10.0       # at 0.10 lot


def load():
    rows = []
    with open(DATA, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                         float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    rows.sort(key=lambda x: x[0])
    return rows


def evaluate(trades, label, cost_pt=COST_PT):
    """trades: list of dicts with t(entry), gross (points, signed P&L pre-cost)."""
    if not trades:
        print(f"{label:<34} NO TRADES")
        return None
    net = [{"t": x["t"], "p": x["gross"] - cost_pt} for x in trades]
    pts = [x["p"] for x in net]
    n = len(pts)
    wins = sum(1 for p in pts if p > 0)
    total = sum(pts)
    # span / trades-per-day
    days = len({x["t"].date() for x in net})
    tpd = n / days if days else 0
    # weekly buckets (ISO year-week)
    wk = {}
    for x in net:
        key = x["t"].isocalendar()[:2]
        wk[key] = wk.get(key, 0.0) + x["p"]
    weeks = list(wk.values())
    green = sum(1 for w in weeks if w > 0)
    pct_green = 100 * green / len(weeks)
    # equity / maxDD in points
    eq = 0.0; peak = 0.0; mdd = 0.0
    for p in pts:
        eq += p; peak = max(peak, eq); mdd = max(mdd, peak - eq)
    gl = sum(p for p in pts if p <= 0); gw = sum(p for p in pts if p > 0)
    pf = gw / abs(gl) if gl else float("inf")
    # per-year net
    yr = {}
    for x in net:
        yr[x["t"].year] = yr.get(x["t"].year, 0.0) + x["p"]
    yline = " ".join(f"{y}:{v:+.0f}" for y, v in sorted(yr.items()))
    print(f"{label:<34} n={n:<5} {tpd:.1f}/d WR={100*wins/n:4.0f}% PF={pf:4.2f} "
          f"exp={total/n:+.3f}pt net={total:+.0f}pt(${total*USD_PER_PT:+,.0f}) "
          f"maxDD={mdd:.0f}pt | GREEN WEEKS={pct_green:.0f}% ({green}/{len(weeks)})")
    print(f"{'':<34} years: {yline}")
    return {"n": n, "tpd": tpd, "exp": total / n, "net": total, "pct_green": pct_green,
            "pf": pf, "mdd": mdd, "weeks": weeks}


# ---------- indicators ----------
def rolling_z(close, L):
    z = [0.0] * len(close)
    from collections import deque
    dq = deque(maxlen=L)
    s = 0.0; s2 = 0.0
    for i, c in enumerate(close):
        if len(dq) == L:
            old = dq[0]; s -= old; s2 -= old * old
        dq.append(c); s += c; s2 += c * c
        if len(dq) == L:
            m = s / L
            var = max(1e-9, s2 / L - m * m)
            z[i] = (c - m) / (var ** 0.5)
    return z


# ---------- Strategy A: hour-gated mean-reversion z-fade ----------
def strat_meanrev(bars, *, hours=range(3, 9), L=24, z_enter=1.8, k_stop=2.5,
                  time_stop=12):
    t = [b[0] for b in bars]; o = [b[1] for b in bars]; h = [b[2] for b in bars]
    lo = [b[3] for b in bars]; c = [b[4] for b in bars]
    z = rolling_z(c, L)
    # rolling std for stop sizing
    from collections import deque
    dq = deque(maxlen=L); s = 0.0; s2 = 0.0; sd = [0.0] * len(c)
    for i, cc in enumerate(c):
        if len(dq) == L:
            old = dq[0]; s -= old; s2 -= old * old
        dq.append(cc); s += cc; s2 += cc * cc
        if len(dq) == L:
            m = s / L; sd[i] = max(1e-6, (s2 / L - m * m)) ** 0.5
    trades = []; i = L + 1; n = len(c)
    while i < n - 1:
        if t[i].hour not in hours or sd[i] <= 0:
            i += 1; continue
        side = None
        if z[i] >= z_enter:
            side = "short"
        elif z[i] <= -z_enter:
            side = "long"
        if side is None:
            i += 1; continue
        entry = o[i + 1]; stopd = k_stop * sd[i]
        j = i + 1; exit_px = None
        while j < n and (j - i) <= time_stop and t[j].hour in list(hours) + [list(hours)[-1] + 1]:
            if side == "long":
                if lo[j] <= entry - stopd:
                    exit_px = entry - stopd; break
                if c[j] >= entry + 0.5 * stopd or z[j] >= -0.1:  # revert to mean
                    exit_px = c[j]; break
            else:
                if h[j] >= entry + stopd:
                    exit_px = entry + stopd; break
                if c[j] <= entry - 0.5 * stopd or z[j] <= 0.1:
                    exit_px = c[j]; break
            j += 1
        if exit_px is None:
            exit_px = c[min(j, n - 1)]
        gross = (exit_px - entry) if side == "long" else (entry - exit_px)
        trades.append({"t": t[i], "gross": gross})
        i = j + 1
    return trades


# ---------- Strategy B: opening-range breakout (London + NY) ----------
def strat_orb(bars, *, sessions=((7, 7, 30), (13, 13, 30)), or_min=30,
              tp_mult=1.5, hold_bars=36):
    """For each session open, build the first `or_min` range, trade the break."""
    t = [b[0] for b in bars]; o = [b[1] for b in bars]; h = [b[2] for b in bars]
    lo = [b[3] for b in bars]; c = [b[4] for b in bars]
    n = len(c); trades = []
    # index bars by date
    by_day = {}
    for idx, tt in enumerate(t):
        by_day.setdefault(tt.date(), []).append(idx)
    for day, idxs in by_day.items():
        for (sh, _eh, _em) in sessions:
            # opening range = bars in [sh:00, sh:00+or_min)
            or_idx = [k for k in idxs if t[k].hour == sh and t[k].minute < or_min]
            if len(or_idx) < 2:
                continue
            rng_hi = max(h[k] for k in or_idx); rng_lo = min(lo[k] for k in or_idx)
            rng = rng_hi - rng_lo
            if rng <= 0:
                continue
            start = or_idx[-1] + 1
            side = None; entry = None
            for k in range(start, min(start + hold_bars, n)):
                if t[k].date() != day:
                    break
                if h[k] >= rng_hi and side is None:
                    side = "long"; entry = rng_hi
                    stop = rng_lo; tp = rng_hi + tp_mult * rng; ek = k; break
                if lo[k] <= rng_lo and side is None:
                    side = "short"; entry = rng_lo
                    stop = rng_hi; tp = rng_lo - tp_mult * rng; ek = k; break
            if side is None:
                continue
            exit_px = None
            for k in range(ek + 1, min(ek + hold_bars, n)):
                if t[k].date() != day:
                    exit_px = c[k - 1]; break
                if side == "long":
                    if lo[k] <= stop:
                        exit_px = stop; break
                    if h[k] >= tp:
                        exit_px = tp; break
                else:
                    if h[k] >= stop:
                        exit_px = stop; break
                    if lo[k] <= tp:
                        exit_px = tp; break
            if exit_px is None:
                exit_px = c[min(ek + hold_bars, n - 1)]
            gross = (exit_px - entry) if side == "long" else (entry - exit_px)
            trades.append({"t": t[ek], "gross": gross})
    trades.sort(key=lambda x: x["t"])
    return trades


if __name__ == "__main__":
    bars = load()
    print(f"loaded {len(bars)} M5 bars  {bars[0][0]} -> {bars[-1][0]}\n")
    print(f"{'STRATEGY':<34} {'stats':<70} weekly-consistency")
    print("-" * 130)

    evaluate(strat_meanrev(bars), "A meanrev z-fade 03-09 UTC")
    evaluate(strat_meanrev(bars, hours=range(0, 24)), "C meanrev z-fade ALL hours (control)")
    evaluate(strat_orb(bars), "B ORB London+NY")
