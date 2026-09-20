"""Fast live feed for the desktop dashboard — writes dashboard/live.json every ~2s.

Small + fast: only price + account (equity/balance/margin) + positions (floating PnL) +
orders, from the MetaApi REST account 6c7ce166. The renderer fast-polls this for a
real-time chart candle and live PnL, while refresh_new.py handles the slow candle history.

Read-only.  .venv/Scripts/python.exe dashboard/refresh_live_px.py
"""
import json, os, re, sys, time
from datetime import datetime, timezone
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
OUT = os.path.join(ROOT, "dashboard", "live.json")
BASE = "https://mt-client-api-v1.london.agiliumtrade.ai"
GOAL = 5500.0
INTERVAL = 2.0
# MetaApi's account-information `margin` field reports NOTIONAL (1x) for this broker;
# real margin on XAUUSD is ~$133 / 0.01 lot => ~30x effective leverage on gold. Recompute
# true margin from position notional so the dashboard matches the MT5 platform.
EFF_LEVERAGE = 30.0
CONTRACT = 100.0  # 1 lot = 100 oz


def envval(key):
    txt = open(ENV, encoding="utf-8").read()
    m = re.search(rf"(?mi)^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", txt)
    return m.group(1).strip().strip('"').strip() if m else None


def main():
    acct, token = envval("meta_id"), envval("access_token")
    H = {"auth-token": token}
    sess = requests.Session()

    def get(path):
        r = sess.get(f"{BASE}/users/current/accounts/{acct}/{path}", headers=H, timeout=15)
        r.raise_for_status()
        return r.json()

    while True:
        try:
            info = get("account-information")
            px = get("symbols/XAUUSD/current-price")
            positions = get("positions")
            orders = get("orders")
            eq = info.get("equity", 0.0) or 0.0
            mid = round((px.get("bid", 0) + px.get("ask", 0)) / 2, 2)
            notional = sum((p.get("volume", 0) * CONTRACT * (p.get("currentPrice") or mid))
                           for p in positions)
            real_margin = round(notional / EFF_LEVERAGE, 2)
            real_free = round(eq - real_margin, 2)
            out = {
                "t": datetime.now(timezone.utc).isoformat(),
                "price": {"bid": px.get("bid"), "ask": px.get("ask"), "mid": mid,
                          "time": px.get("time")},
                "account": {"balance": info.get("balance"), "equity": eq,
                            "margin": real_margin, "freeMargin": real_free,
                            "marginRaw": info.get("margin"), "leverageEff": EFF_LEVERAGE},
                "positions": positions,
                "orders": orders,
                "goal": GOAL, "to_goal": round(GOAL - eq, 2),
                "floating": round(sum(p.get("profit", 0) for p in positions), 2),
            }
            tmp = OUT + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(out, f)
            os.replace(tmp, OUT)
        except Exception as e:
            print(f"[live] {e}", file=sys.stderr)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
