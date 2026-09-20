"""Tests for bot.challenge_xau — the challenge-safe H4 trend-follow strategy.
Run: .venv/Scripts/python.exe test_challenge_xau.py
Hand-rolled asserts (matches test_trade_history.py style), NOT pytest.
"""
import csv
import datetime as dt
import os

from bot import challenge_xau as S

PASS, FAIL = [], []
def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + (("  -> " + extra) if extra else ""))


# --- position sizing: a -1R loss must stay inside a $5k challenge daily limit ---
lot, risk = S.position_size(5000, atr_now=8.0)          # ATR ~8 pts on H4
check("size returns a tradeable lot", lot >= 0.01, f"lot={lot}")
check("a -1R loss (~risk$) stays under $250 daily limit", risk <= 250, f"risk=${risk}")
check("risk is meaningful (not dust)", risk >= 30, f"risk=${risk}")
# higher ATR -> smaller lot (risk held ~constant)
lot_hi, risk_hi = S.position_size(5000, atr_now=20.0)
check("higher ATR -> smaller lot", lot_hi <= lot, f"{lot_hi} <= {lot}")
check("risk stays bounded as ATR rises", risk_hi <= 250, f"risk=${risk_hi}")

# --- signal: synthetic uptrend breakout fires long; downtrend fires short ---
# h/l == c so each new close is a fresh Donchian high (a clean breakout series).
up = [3000 + i for i in range(120)]                      # monotonic up
sig, entry, stop, a = S.signal(up, up, up, up)
check("uptrend breakout -> long", sig == "long", str(sig))
check("long stop below entry", stop is not None and stop < entry, f"{stop} < {entry}")
down = [3000 - i for i in range(120)]
sig2, e2, s2, a2 = S.signal(down, down, down, down)
check("downtrend breakout -> short", sig2 == "short", str(sig2))
check("short stop above entry", s2 is not None and s2 > e2, f"{s2} > {e2}")
# flat market -> no trade
flat = [3000] * 120
sig3, *_ = S.signal(flat, flat, flat, flat)
check("flat market -> no signal", sig3 is None, str(sig3))

# --- integration: the real H4 data must show a positive, capped edge ---
path = os.path.join("reports", "xau_h4_3y.csv")
if os.path.exists(path):
    bars = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bars.append((dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                         float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    s = S.summary(S.backtest(bars))
    print(f"  (H4 backtest: n={s['n']} WR={s['wr']:.0f}% PF={s['pf']:.2f} "
          f"net=${s['net']:+.0f} exp=${s['exp']:+.1f} worstR={s['worst_R']:+.2f})")
    check("H4 edge is positive expectancy", s["exp"] > 0, f"exp={s['exp']:.2f}")
    check("H4 profit factor > 1.3", s["pf"] > 1.3, f"pf={s['pf']:.2f}")
    check("downside capped near -1R by the stop", s["worst_R"] >= -1.6, f"worstR={s['worst_R']:.2f}")
else:
    print("  (skipping integration test: reports/xau_h4_3y.csv not present)")

print(f"\n=== RESULT: {len(PASS)} passed, {len(FAIL)} failed ===")
if FAIL:
    raise SystemExit(1)
print("ALL GREEN")
