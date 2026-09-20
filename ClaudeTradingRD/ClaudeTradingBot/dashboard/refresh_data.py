"""Read-only data refresher for the dashboard.

Pulls account info / positions / orders from the broker, XAUUSD price+candles
from OANDA (bot.data) and BTCUSDT price+candles from the MT5 terminal feed
(bot.data_mt5), then writes dashboard/data.json.

Run from the project root with the venv python so `bot` imports resolve:
    C:\\Projects\\ClaudeProjects\\ClaudeTradingBot\\.venv\\Scripts\\python.exe dashboard\\refresh_data.py

IMPORTANT: this script NEVER places, modifies or closes trades. Read-only.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

# Ensure project root is importable even if invoked from elsewhere.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)  # so .env loads via dotenv defaults

from bot import broker, data, data_mt5  # noqa: E402
from bot import polymarket, kalshi  # noqa: E402
from bot import trade_history  # noqa: E402

OUT_PATH = os.path.join(ROOT, "dashboard", "data.json")
TIMEFRAMES = ["M15", "H1", "H4", "D"]
# Low TFs come from the MT5 terminal for BOTH symbols: OANDA has no M3
# granularity, and MT5 matches the execution venue's prices.
LOW_TFS = ["M1", "M3", "M5"]


def safe(fn, default, label):
    try:
        return fn()
    except Exception as e:  # keep dashboard alive on partial failures
        print(f"[refresh] WARN {label}: {e}", file=sys.stderr)
        return default


def main():
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "account": safe(broker.account_information, {}, "account-information"),
        "positions": safe(broker.positions, [], "positions"),
        "orders": safe(broker.pending_orders, [], "orders"),
        "price": safe(data.current_price, {}, "oanda price"),
    }

    symbols = {
        "XAUUSD": {"price": out["price"], "candles": {}},
        "BTCUSDT": {"price": safe(lambda: data_mt5.current_price("BTCUSDT"),
                                  {}, "btc price"), "candles": {}},
    }
    for tf in TIMEFRAMES:
        symbols["XAUUSD"]["candles"][tf] = safe(
            lambda tf=tf: data.candles(granularity=tf, count=200),
            [], f"XAU candles {tf}")
        symbols["BTCUSDT"]["candles"][tf] = safe(
            lambda tf=tf: data_mt5.candles("BTCUSDT", tf, 200),
            [], f"BTC candles {tf}")
        time.sleep(0.2)  # be gentle with the API
    for tf in LOW_TFS:
        for sym in ("XAUUSD", "BTCUSDT"):
            symbols[sym]["candles"][tf] = safe(
                lambda s=sym, tf=tf: data_mt5.candles(s, tf, 300),
                [], f"{sym} candles {tf}")
    out["symbols"] = symbols
    out["candles"] = symbols["XAUUSD"]["candles"]  # legacy renderer key

    # Prediction-market BTC odds (read-only public APIs). Confluence for BTC
    # trades + a market-implied read on the Iran-deal gold/BTC binary.
    btc_spot = (symbols["BTCUSDT"]["price"] or {}).get("mid")
    out["bets"] = {
        "polymarket": safe(polymarket.snapshot, {}, "polymarket"),
        "kalshi": safe(lambda: kalshi.snapshot(spot=btc_spot), {}, "kalshi"),
    }

    # Per-symbol order history (the trades THIS app took), reconstructed from the
    # local journal/orders.csv. Broker-free, so it survives an MT5 outage.
    out["trades"] = safe(trade_history.load_trades, {}, "trade-history")

    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    os.replace(tmp, OUT_PATH)  # atomic-ish swap so the renderer never reads half a file
    print(f"[refresh] wrote {OUT_PATH} at {out['generated_at']} "
          f"(positions={len(out['positions'])}, orders={len(out['orders'])}, "
          f"btc={symbols['BTCUSDT']['price'].get('mid', 'n/a')})")


if __name__ == "__main__":
    main()
