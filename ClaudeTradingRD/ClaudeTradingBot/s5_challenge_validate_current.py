"""Validate bot/challenge_xau.py against CURRENT data.

1. Pull a fresh single-source OANDA H4 XAU_USD series through today (complete bars).
2. Run the strategy backtest; break results down per calendar year + the last 90 days.
3. Re-run on the committed reports/xau_h4_3y.csv (deduped) as a cross-check.
Read-only. Places no trades.
"""
import csv
import datetime as dt
import os

from bot import data as D
from bot import challenge_xau as S


def fetch_oanda_h4(count=5000):
    rows = D.candles(granularity="H4", count=count, price="M")
    bars = []
    for r in rows:
        if not r["complete"]:
            continue
        t = dt.datetime.strptime(r["time"][:19], "%Y-%m-%dT%H:%M:%S")
        bars.append((t, r["o"], r["h"], r["l"], r["c"]))
    bars.sort(key=lambda b: b[0])
    # dedup identical timestamps
    seen, out = set(), []
    for b in bars:
        if b[0] in seen:
            continue
        seen.add(b[0]); out.append(b)
    return out


def load_csv(path):
    bars = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bars.append((dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                         float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    seen, out = set(), []
    for b in bars:
        if b[0] in seen:
            continue
        seen.add(b[0]); out.append(b)
    return out


def report(label, bars):
    print(f"\n========== {label} ==========")
    print(f"bars: {len(bars)}  range: {bars[0][0]} -> {bars[-1][0]}")
    trades = S.backtest(bars)
    s = S.summary(trades)
    print(f"OVERALL  n={s['n']} WR={s['wr']:.0f}% PF={s['pf']:.2f} "
          f"net=${s['net']:+.0f} exp=${s['exp']:+.1f} worstR={s['worst_R']:+.2f}")
    # per-year
    print("per-year:")
    for yr in sorted({t['t'].year for t in trades}):
        yt = [t for t in trades if t['t'].year == yr]
        sy = S.summary(yt)
        flag = "" if sy['net'] > 0 else "   <-- NEGATIVE"
        print(f"  {yr}: n={sy['n']:>3} WR={sy['wr']:>3.0f}% PF={sy['pf']:>4.2f} "
              f"net=${sy['net']:>+7.0f} worstR={sy['worst_R']:+.2f}{flag}")
    # last 90 days (the genuinely "current" slice)
    cutoff = bars[-1][0] - dt.timedelta(days=90)
    recent = [t for t in trades if t['t'] >= cutoff]
    if recent:
        sr = S.summary(recent)
        print(f"last 90d: n={sr['n']} WR={sr['wr']:.0f}% PF={sr['pf']:.2f} "
              f"net=${sr['net']:+.0f} worstR={sr['worst_R']:+.2f}")
        print("  recent trades:")
        for t in recent[-8:]:
            print(f"    {t['t']}  {t['side']:<5} R={t['R']:+.2f}  pnl=${t['pnl']:+.0f}")
    return s


fresh = fetch_oanda_h4()
s_fresh = report("FRESH OANDA H4 (current)", fresh)

csv_path = os.path.join("reports", "xau_h4_3y.csv")
if os.path.exists(csv_path):
    s_csv = report("COMMITTED xau_h4_3y.csv (deduped)", load_csv(csv_path))

print("\n=== VERDICT ===")
ok = s_fresh['pf'] > 1.3 and s_fresh['exp'] > 0 and s_fresh['worst_R'] >= -1.6
print(("PASS" if ok else "FAIL") +
      f" on current data: PF={s_fresh['pf']:.2f} exp=${s_fresh['exp']:+.1f} "
      f"worstR={s_fresh['worst_R']:+.2f}")
