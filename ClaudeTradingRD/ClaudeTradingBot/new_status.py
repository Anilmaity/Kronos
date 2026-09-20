"""Read-only snapshot of the ACTIVE FundingPips account (goal: equity -> $5,500).

Uses the new MetaApi account/token (the free-form `meta_id` / `access_token`
lines in .env), NOT the legacy META_ACCOUNT_ID. Pure REST, read-only — it never
places, modifies, or closes anything.

    .venv/Scripts/python.exe new_status.py
"""
import os
import re
import sys
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(ROOT, ".env")
BASE = "https://mt-client-api-v1.london.agiliumtrade.ai"
GOAL = 5500.0


def _from_env(key):
    """Read a free-form `key = value` line from .env (tolerates quotes/spaces)."""
    try:
        txt = open(ENV, encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(rf"(?mi)^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", txt)
    return m.group(1).strip().strip('"').strip() if m else None


def main():
    acct = _from_env("meta_id")
    token = _from_env("access_token")
    if not acct or not token:
        sys.exit("missing meta_id/access_token in .env")
    h = {"auth-token": token}

    def get(path):
        r = requests.get(f"{BASE}/users/current/accounts/{acct}/{path}",
                         headers=h, timeout=30)
        r.raise_for_status()
        return r.json()

    info = get("account-information")
    eq = info.get("equity", 0.0)
    bal = info.get("balance", 0.0)
    px = get("symbols/XAUUSD/current-price")
    pos = get("positions")
    orders = get("orders")

    # Real margin: MetaApi `margin` field reports notional; gold is ~30x (~$133/0.01 lot).
    EFF_LEVERAGE, CONTRACT = 30.0, 100.0
    mid = (px.get("bid", 0) + px.get("ask", 0)) / 2
    notional = sum(p.get("volume", 0) * CONTRACT * (p.get("currentPrice") or mid) for p in pos)
    real_margin = notional / EFF_LEVERAGE
    real_free = eq - real_margin

    print(f"ACCOUNT  {info.get('broker')} / {info.get('server')}  login {info.get('login')}")
    print(f"BALANCE  ${bal:,.2f}   EQUITY ${eq:,.2f}   "
          f"GOAL ${GOAL:,.0f}  (need ${GOAL - eq:+,.2f}, {100*(GOAL-eq)/eq:+.2f}%)")
    print(f"MARGIN   ${real_margin:,.2f} used / ${real_free:,.2f} free  "
          f"(~{EFF_LEVERAGE:.0f}x gold; MetaApi notional field = ${info.get('margin',0):,.2f})")
    print(f"XAUUSD   bid {px['bid']}  ask {px['ask']}  @ {px['time']}")
    print(f"POSITIONS ({len(pos)}):")
    for p in pos:
        print(f"  {p['type']} {p['volume']} @ {p['openPrice']}  SL {p.get('stopLoss')} "
              f"TP {p.get('takeProfit')}  P/L ${p.get('profit', 0):.2f}  id {p['id']}")
    print(f"PENDING ({len(orders)}):")
    for o in orders:
        print(f"  {o['type']} {o['volume']} @ {o['openPrice']}  SL {o.get('stopLoss')} "
              f"TP {o.get('takeProfit')}  id {o['id']}  [{o['state']}]")


if __name__ == "__main__":
    main()
