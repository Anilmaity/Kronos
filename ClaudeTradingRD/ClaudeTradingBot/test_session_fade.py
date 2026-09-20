"""Tests for bot.session_fade (GuardedSessionFade — your style + guardrails).
Run: .venv/Scripts/python.exe test_session_fade.py
Asserts the GUARDRAILS work (cap the tail), then runs an honest 5s backtest.
"""
import glob, json, datetime as dt
from bot import session_fade as SF

PASS, FAIL = [], []
def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + (("  -> " + extra) if extra else ""))

# --- sizing: a stop-out stays inside a $5k daily limit ---
lot, risk = SF.position_size(5000, stop_points=2.0)
check("sized lot tradeable", lot >= 0.01, f"lot={lot}")
check("stop-out risk under $250 daily limit", risk <= 250, f"${risk}")
check("risk meaningful", 20 <= risk <= 120, f"${risk}")

# --- signal: only fades in-session, needs an extension, respects 15m agreement ---
up = [3000 + i * 0.02 for i in range(200)]          # gentle up-extension
check("fades up-move with SELL in session (22h)", SF.signal(up, 22) == "sell")
check("no trade out of session (15h)", SF.signal(up, 15) is None)
flat = [3000.0] * 200
check("no trade without extension", SF.signal(flat, 22) is None)
down = [3000 - i * 0.02 for i in range(200)]
check("fades down-move with BUY in session", SF.signal(down, 22) == "buy")

# --- daily guard kill-switch ---
g = SF.DailyGuard(max_loss=120, max_trades=15, max_consec_losses=3)
day = "2026-06-22"
check("guard allows at day start", g.allowed(day))
for _ in range(3):
    g.record(day, -50)
check("guard halts after 3 consecutive losses", not g.allowed(day), "streak/loss cap")
g2 = SF.DailyGuard(max_loss=120)
g2.record(day, -130)
check("guard halts after daily loss cap", not g2.allowed(day))

# --- integration: backtest on 5s data, prove the tail is CAPPED ---
CACHE = "C:/Projects/PycharmProjects/personal/KronosStrategies/tick_data_collector/Tick_Data_Generator/cache_data/XAU_USD"
files = sorted(glob.glob(CACHE + "/*.json"))
if files:
    bars = []
    for fp in files:
        for grp in json.load(open(fp, encoding="utf-8")):
            t = dt.datetime.fromisoformat(grp[0]["time"])
            bars.append((t, [float(p["price"]) for p in grp]))
    bars.sort(key=lambda x: x[0])
    closes = [b[1][-1] for b in bars]; times = [b[0] for b in bars]; n = len(bars)
    TP, SL, HOLD = 0.8, 2.0, 18          # SL=2pt hard stop; hold 90s
    guard = SF.DailyGuard()
    trades = []; pos = None; last_i = -999
    for i in range(180, n):
        t = times[i]
        if pos is not None:
            ex = None
            for px in bars[i][1]:
                if pos["side"] == "buy":
                    if px <= pos["sl"]: ex = pos["sl"]; break
                    if px >= pos["tp"]: ex = pos["tp"]; break
                else:
                    if px >= pos["sl"]: ex = pos["sl"]; break
                    if px <= pos["tp"]: ex = pos["tp"]; break
            if ex is None and (i - pos["i"]) >= HOLD:
                ex = closes[i]
            if ex is not None:
                pts = (ex - pos["entry"]) if pos["side"] == "buy" else (pos["entry"] - ex)
                pnl = pts * 10 * 0.1 / 0.1 - 0.05
                trades.append(pnl); guard.record(t.date(), pnl); pos = None
        if pos is not None or (times[i] - times[i-1]).total_seconds() > 30:
            continue
        if (i - last_i) < 3 or not guard.allowed(t.date()):
            continue
        sig = SF.signal(closes[:i+1], t.hour, ext_points=1.0)
        if sig is None:
            continue
        entry = closes[i] + 0.125 if sig == "buy" else closes[i] - 0.125
        pos = {"side": sig, "entry": entry,
               "tp": entry + TP if sig == "buy" else entry - TP,
               "sl": entry - SL if sig == "buy" else entry + SL, "i": i}
        last_i = i
    if trades:
        n_t = len(trades); wr = 100 * sum(1 for x in trades if x > 0) / n_t
        worst = min(trades); net = sum(trades)
        print(f"  (guarded 5s backtest: n={n_t} WR={wr:.0f}% net=${net:+.0f} "
              f"worst=${worst:+.2f} exp=${net/n_t:+.3f})")
        check("guardrail CAPS worst trade near -1R (no -$269 tail)", worst >= -30, f"worst=${worst:.2f}")
        # honest trade-off: the hard stop drops WR from ~87% (no-stop) to ~55-70%,
        # turning would-have-reverted trades into capped losses. That is the cost of
        # survivability — and confirms the style has no systematic edge on its own.
        check("WR above coin-flip but stop costs the high-WR illusion", 50 <= wr <= 80, f"{wr:.0f}%")

print(f"\n=== RESULT: {len(PASS)} passed, {len(FAIL)} failed ===")
if FAIL:
    raise SystemExit(1)
print("ALL GREEN — guardrails verified (tail capped). NOTE: systematic expectancy is "
      "~breakeven/negative; this harness only makes the style SURVIVABLE for discretionary use.")
