"""Unit tests for bot.trade_history (orders.csv -> per-symbol trade records).
Run: .venv/Scripts/python.exe test_trade_history.py
Hand-rolled asserts (matches test_arb_gate.py / test_never_naked.py style), NOT pytest.
"""
import os
import tempfile

from bot import trade_history as th

PASS, FAIL = [], []
def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + (("  -> " + extra) if extra else ""))


HEADER = ("timestamp_utc,event,symbol,side,lots,price,sl,tp,risk_usd,rr,"
          "order_id,position_id,profit_usd,balance_after,notes\n")

# Synthetic log exercising every shape the real journal/orders.csv contains:
#  - a clean open/close pair (win)
#  - a messy backfill scale-in where BOTH rows are event=backfill_close (the
#    first is really the entry) -> must still pair into one closed trade
#  - a pending order that was cancelled before filling -> "cancelled", no P&L
#  - an open with only a later modify -> still "open"
#  - a pending_open still resting -> "open"
ROWS = [
    "2026-06-12 10:00:00,open,XAUUSD,sell,0.01,4107.75,,,,,1,1,,,liq-sweep-short",
    "2026-06-12 10:30:00,close,XAUUSD,buy,0.01,4093.15,,,,,991,1,14.60,963.39,[tp]",
    "2026-06-11 10:50:55,backfill_close,XAUUSD,buy,0.03,4100.09,,,,,2,2,0.0,,tg-5835",
    "2026-06-11 11:00:47,backfill_close,XAUUSD,sell,0.03,4110.07,,,,,88,2,29.94,,[tp]",
    "2026-06-14 17:41:11,pending_open,BTCUSDT,sell,0.03,63880.0,64010.0,63560.0,3.9,2.46,3,3,,,fade",
    "2026-06-14 18:00:00,cancel_pending,BTCUSDT,sell,0.03,63880.0,,,,,3,3,,1057.33,stale-cancel",
    "2026-06-13 22:29:37,open,BTCUSDT,buy,0.03,64498.45,64260.0,65000.0,7.15,2.1,4,4,,,ob-retest",
    "2026-06-13 23:00:00,modify,,,,,64300,65000,,,,4,,,,",
    "2026-06-15 08:34:39,pending_open,XAUUSD,buy,0.01,4335.5,4325.5,4355.5,10.0,2.0,5,5,,,discount-limit",
]


def _write(rows):
    fd, p = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(HEADER)
        f.write("\n".join(rows) + "\n")
    return p


path = _write(ROWS)
res = th.load_trades(path)

xau = res["XAUUSD"]
btc = res["BTCUSDT"]
by_pid = {t["position_id"]: t for t in xau + btc}

# --- pairing & status ---
check("XAUUSD has 3 trades (2 closed + 1 pending)", len(xau) == 3, str(len(xau)))
check("BTCUSDT has 2 trades (1 open + 1 cancelled)", len(btc) == 2, str(len(btc)))

t1 = by_pid["1"]
check("clean pair: entry side=sell", t1["side"] == "sell", t1["side"])
check("clean pair: entry price 4107.75", t1["entry_price"] == 4107.75, str(t1["entry_price"]))
check("clean pair: exit price 4093.15", t1["exit_price"] == 4093.15, str(t1["exit_price"]))
check("clean pair: pnl 14.60", abs(t1["profit_usd"] - 14.60) < 1e-9, str(t1["profit_usd"]))
check("clean pair: status closed", t1["status"] == "closed", t1["status"])
check("clean pair: intent carried", t1["notes"] == "liq-sweep-short", t1["notes"])

t2 = by_pid["2"]
check("messy backfill scale-in pairs into one closed trade", t2["status"] == "closed", t2["status"])
check("messy backfill: entry side=buy (first row)", t2["side"] == "buy", t2["side"])
check("messy backfill: entry 4100.09", t2["entry_price"] == 4100.09, str(t2["entry_price"]))
check("messy backfill: exit 4110.07", t2["exit_price"] == 4110.07, str(t2["exit_price"]))
check("messy backfill: pnl 29.94", abs(t2["profit_usd"] - 29.94) < 1e-9, str(t2["profit_usd"]))

t3 = by_pid["3"]
check("cancelled pending -> status cancelled", t3["status"] == "cancelled", t3["status"])
check("cancelled pending -> no pnl", t3["profit_usd"] is None, str(t3["profit_usd"]))

t4 = by_pid["4"]
check("open + modify only -> status open", t4["status"] == "open", t4["status"])
check("open: no exit price", t4["exit_price"] is None, str(t4["exit_price"]))

t5 = by_pid["5"]
check("resting pending_open -> status open", t5["status"] == "open", t5["status"])

# --- ordering: newest entry first ---
check("XAUUSD newest-first by entry time",
      [t["position_id"] for t in xau] == ["5", "1", "2"],
      str([t["position_id"] for t in xau]))

# --- summaries computed over CLOSED trades only ---
sx = res["summary"]["XAUUSD"]
check("XAU summary closed=2", sx["closed"] == 2, str(sx["closed"]))
check("XAU summary wins=2", sx["wins"] == 2, str(sx["wins"]))
check("XAU summary losses=0", sx["losses"] == 0, str(sx["losses"]))
check("XAU summary win_rate=100", sx["win_rate"] == 100.0, str(sx["win_rate"]))
check("XAU summary net_pnl=44.54", abs(sx["net_pnl"] - 44.54) < 1e-9, str(sx["net_pnl"]))
check("XAU summary open=1", sx["open"] == 1, str(sx["open"]))

sb = res["summary"]["BTCUSDT"]
check("BTC summary closed=0", sb["closed"] == 0, str(sb["closed"]))
check("BTC summary open=1", sb["open"] == 1, str(sb["open"]))
check("BTC summary cancelled=1", sb["cancelled"] == 1, str(sb["cancelled"]))
check("BTC summary net_pnl=0", sb["net_pnl"] == 0.0, str(sb["net_pnl"]))

sa = res["summary"]["all"]
check("ALL summary net_pnl=44.54", abs(sa["net_pnl"] - 44.54) < 1e-9, str(sa["net_pnl"]))
check("ALL summary closed=2", sa["closed"] == 2, str(sa["closed"]))

# --- robustness: missing file -> empty structure, no crash ---
empty = th.load_trades(os.path.join(tempfile.gettempdir(), "definitely_missing_orders.csv"))
check("missing file -> empty XAUUSD list", empty["XAUUSD"] == [], str(empty["XAUUSD"]))
check("missing file -> summary present", "all" in empty["summary"], str(empty["summary"].keys()))

# --- integration: the REAL journal must parse without error ---
real = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal", "orders.csv")
if os.path.exists(real):
    r = th.load_trades(real)
    check("real orders.csv parses", isinstance(r["XAUUSD"], list) and isinstance(r["BTCUSDT"], list))
    check("real orders.csv has XAU trades", len(r["XAUUSD"]) > 0, str(len(r["XAUUSD"])))
    print(f"  (real: XAU={len(r['XAUUSD'])} trades net ${r['summary']['XAUUSD']['net_pnl']:.2f}, "
          f"BTC={len(r['BTCUSDT'])} trades net ${r['summary']['BTCUSDT']['net_pnl']:.2f})")

os.unlink(path)
print(f"\n=== RESULT: {len(PASS)} passed, {len(FAIL)} failed ===")
if FAIL:
    raise SystemExit(1)
print("ALL GREEN")
