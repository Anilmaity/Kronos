"""Dashboard refresher for the ACTIVE FundingPips account (goal: equity -> $5,500).

Pulls account / positions / orders from the new MetaApi account (the free-form
`meta_id` / `access_token` in .env) via raw REST, and XAUUSD price+candles from
OANDA (bot.data). Writes dashboard/data.json in the shape renderer.js expects,
preserving the existing BTC / bets / trades sections so nothing in the UI breaks.

Read-only: never places, modifies, or closes a trade.

    .venv/Scripts/python.exe dashboard/refresh_new.py
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from bot import data  # noqa: E402  (OANDA XAU candles + price)

ENV = os.path.join(ROOT, ".env")
OUT_PATH = os.path.join(ROOT, "dashboard", "data.json")
BASE = "https://mt-client-api-v1.london.agiliumtrade.ai"
TIMEFRAMES = ["M15", "H1", "H4", "D"]
GOAL = 5500.0


def _resample(m1, factor):
    """Build a higher low-TF (e.g. M3) by bucketing M1 candles (OANDA has no M3)."""
    if not m1:
        return []
    secs = 60 * factor
    out, cur, bucket = [], None, None
    for c in m1:
        ep = int(__import__("calendar").timegm(
            __import__("time").strptime(c["time"][:19], "%Y-%m-%dT%H:%M:%S")))
        b = ep - (ep % secs)
        if b != bucket:
            if cur:
                out.append(cur)
            bucket = b
            cur = {"time": c["time"], "o": c["o"], "h": c["h"], "l": c["l"],
                   "c": c["c"], "volume": c.get("volume", 0), "complete": c.get("complete", True)}
        else:
            cur["h"] = max(cur["h"], c["h"]); cur["l"] = min(cur["l"], c["l"])
            cur["c"] = c["c"]; cur["volume"] += c.get("volume", 0)
            cur["complete"] = c.get("complete", True)
    if cur:
        out.append(cur)
    return out


def _from_env(key):
    txt = open(ENV, encoding="utf-8").read()
    m = re.search(rf"(?mi)^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", txt)
    return m.group(1).strip().strip('"').strip() if m else None


def main():
    acct = _from_env("meta_id")
    token = _from_env("access_token")
    if not acct or not token:
        sys.exit("missing meta_id/access_token in .env")
    h = {"auth-token": token}

    def get(path, default):
        try:
            r = requests.get(f"{BASE}/users/current/accounts/{acct}/{path}",
                             headers=h, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # keep the dashboard alive on partial failures
            print(f"[refresh_new] WARN {path}: {e}", file=sys.stderr)
            return default

    # Preserve existing BTC / bets / trades so the renderer keeps working.
    try:
        prev = json.load(open(OUT_PATH, encoding="utf-8"))
    except Exception:
        prev = {}

    info = get("account-information", {})
    positions = get("positions", [])
    orders = get("orders", [])
    mp = get("symbols/XAUUSD/current-price", {})
    price = {"bid": mp.get("bid"), "ask": mp.get("ask"),
             "mid": round((mp.get("bid", 0) + mp.get("ask", 0)) / 2, 2) if mp else None,
             "time": mp.get("time")}

    candles = {}
    for tf in TIMEFRAMES:
        try:
            candles[tf] = data.candles(granularity="D" if tf == "D" else tf, count=200)
        except Exception as e:
            print(f"[refresh_new] WARN XAU {tf}: {e}", file=sys.stderr)
            candles[tf] = []
        time.sleep(0.15)
    # Low timeframes from OANDA (M1, M5). OANDA has no M3 -> synthesize it from M1.
    try:
        m1 = data.candles(granularity="M1", count=400)
        candles["M1"] = m1
        candles["M3"] = _resample(m1, 3)
    except Exception as e:
        print(f"[refresh_new] WARN XAU M1/M3: {e}", file=sys.stderr)
        candles.setdefault("M1", []); candles.setdefault("M3", [])
    try:
        candles["M5"] = data.candles(granularity="M5", count=400)
    except Exception as e:
        print(f"[refresh_new] WARN XAU M5: {e}", file=sys.stderr)
        candles["M5"] = []

    eq = info.get("equity", 0.0) or 0.0
    info = dict(info)
    info["goal"] = GOAL
    info["to_goal"] = round(GOAL - eq, 2)
    info["goal_pct"] = round(100 * (GOAL - eq) / eq, 2) if eq else None
    # Real margin: MetaApi reports notional in `margin`; gold is ~30x ($133/0.01 lot).
    EFF_LEVERAGE, CONTRACT = 30.0, 100.0
    notional = sum((p.get("volume", 0) * CONTRACT * (p.get("currentPrice") or price.get("mid") or 0))
                   for p in positions)
    info["marginRaw"] = info.get("margin")
    info["margin"] = round(notional / EFF_LEVERAGE, 2)
    info["freeMargin"] = round(eq - info["margin"], 2)
    info["leverageEff"] = EFF_LEVERAGE

    prev_symbols = prev.get("symbols", {}) if isinstance(prev, dict) else {}
    btc = prev_symbols.get("BTCUSDT", {"price": {}, "candles": {}})

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "account": info,
        "positions": positions,
        "orders": orders,
        "price": price,
        "symbols": {
            "XAUUSD": {"price": price, "candles": candles},
            "BTCUSDT": btc,
        },
        "candles": candles,  # legacy renderer key
        "bets": prev.get("bets", {}) if isinstance(prev, dict) else {},
        "trades": prev.get("trades", {}) if isinstance(prev, dict) else {},
    }

    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    os.replace(tmp, OUT_PATH)
    print(f"[refresh_new] wrote {OUT_PATH} @ {out['generated_at']} | "
          f"equity ${eq:,.2f} (need ${GOAL - eq:+,.2f}) | "
          f"pos={len(positions)} pending={len(orders)} | "
          f"XAU mid {price['mid']} | candles "
          + ",".join(f"{tf}:{len(candles[tf])}" for tf in TIMEFRAMES))


if __name__ == "__main__":
    main()
