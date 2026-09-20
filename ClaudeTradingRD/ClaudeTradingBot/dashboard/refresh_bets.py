"""Lightweight, broker-free bets feed for the dashboard.

Writes dashboard/bets.json on a fast loop (default every 15s) with live
Polymarket (CLOB) + Kalshi (trades) BTC odds, including the rolling 5-minute
Up/Down market. Decoupled from refresh_data.py on purpose: the 5-min prices
move fast and must update reliably WITHOUT hammering the MT5/OANDA broker
feeds (which the heavy refresh_data.py loop owns on a slower 60s cadence).

Run (loop):  ...\\.venv\\Scripts\\python.exe dashboard\\refresh_bets.py
Run (once):  ...\\.venv\\Scripts\\python.exe dashboard\\refresh_bets.py --once
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)  # so .env / dotenv defaults resolve

from bot import polymarket, kalshi, funding, arbitrage, data_mt5  # noqa: E402

OUT_PATH = os.path.join(ROOT, "dashboard", "bets.json")
INTERVAL = 15  # seconds — fast enough for a 5-min market, gentle on the APIs


def _btc_inputs():
    """Live BTC spot + M1 candles for the edge model (broker read, best-effort)."""
    try:
        spot = data_mt5.current_price("BTCUSDT").get("mid")
        m1 = [c for c in data_mt5.candles("BTCUSDT", "M1", 60) if c["complete"]]
        return spot, m1
    except Exception:
        return None, []


def build():
    poly = polymarket.snapshot()
    spot, m1 = _btc_inputs()
    # Center Kalshi strikes near spot (falls back to median strike if absent).
    kal = kalshi.snapshot(spot=spot or (poly.get("btc_cdf") or {}).get("implied_pivot"))
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "polymarket": poly,
        "kalshi": kal,
    }
    try:
        out["funding"] = funding.snapshot()
    except Exception as e:
        out["funding_error"] = str(e)
    try:
        out["signals"] = arbitrage.build_signals(
            spot=spot, m1_candles=m1, updown=poly.get("updown_5m"),
            poly_cdf=poly.get("btc_cdf"), kalshi_cdf=kal.get("btc_cdf"))
    except Exception as e:
        out["signals_error"] = str(e)
    return out


def write_once():
    out = build()
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    os.replace(tmp, OUT_PATH)  # atomic swap so the renderer never reads a half file
    up = None
    w = (out["polymarket"].get("updown_5m") or {}).get("windows") or []
    if w:
        up = w[0].get("up_prob")
    print(f"[bets] wrote {out['generated_at']} "
          f"(5m UP={up}, poly_pivot={(out['polymarket'].get('btc_cdf') or {}).get('implied_pivot')}, "
          f"kalshi_live={out['kalshi'].get('quotes_available')})", flush=True)


def main():
    once = "--once" in sys.argv
    while True:
        try:
            write_once()
        except Exception as e:  # never let one bad fetch kill the loop
            print(f"[bets] WARN {e}", file=sys.stderr, flush=True)
        if once:
            return
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
