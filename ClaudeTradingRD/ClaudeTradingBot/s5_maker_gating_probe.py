"""GATING PROBE: is FundingPips acct 6c7ce166 maker-capable or taker-only?

Decisive evidence = the XAUUSD symbol specification's executionMode.
  EXCHANGE  -> real order book, resting limits provide liquidity = MAKER-capable
  MARKET/INSTANT/REQUEST -> dealer-quote model, every fill crosses spread = TAKER-only

Also dumps fillingModes + live bid/ask spread. Read-only; places NO trades.
"""
import os
import re
import sys
import requests

BASE = "https://mt-client-api-v1.london.agiliumtrade.ai"


def load_env(path=".env"):
    env = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main():
    env = load_env()
    # New account creds (free-form lines), per trading-bot-connections memory.
    acct = env.get("meta_id") or env.get("META_ACCOUNT_ID")
    token = env.get("access_token") or env.get("META_API_TOKEN")
    if not acct or not token:
        sys.exit("Missing meta_id/access_token in .env")
    print(f"account: {acct[:8]}...  (token {token[:6]}...)")

    headers = {"auth-token": token, "Content-Type": "application/json"}
    root = f"{BASE}/users/current/accounts/{acct}"

    import time

    def get(path, retries=8, backoff=5):
        last = None
        for i in range(retries):
            try:
                r = requests.get(f"{root}/{path}", headers=headers, timeout=30)
                if r.status_code in (502, 504):
                    last = f"{r.status_code} {r.text[:120]}"
                    print(f"  [{path}] {r.status_code} retry {i+1}/{retries}...")
                    time.sleep(backoff)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                last = str(e)
                time.sleep(backoff)
        raise RuntimeError(f"GET {path} failed after {retries} tries: {last}")

    # Connection state first — a 504 storm usually means the account isn't deployed/connected.
    print("checking account-information (connection state)...")
    info = get("account-information")
    print(f"  connected. balance={info.get('balance')} equity={info.get('equity')} "
          f"broker={info.get('broker')!r} server={info.get('server')!r}")

    spec = get("symbols/XAUUSD/specification")
    price = get("symbols/XAUUSD/current-price")

    em = spec.get("executionMode") or spec.get("tradeExecutionMode")
    fills = spec.get("fillingModes") or spec.get("fillingMode")
    bid, ask = price.get("bid"), price.get("ask")
    spread = round(ask - bid, 3) if bid and ask else None

    print("\n--- XAUUSD specification (account 6c7ce166) ---")
    print(f"executionMode : {em}")
    print(f"fillingModes  : {fills}")
    print(f"tradeMode     : {spec.get('tradeMode')}")
    print(f"contractSize  : {spec.get('contractSize')}")
    print(f"minVolume     : {spec.get('minVolume')}  step {spec.get('volumeStep')}")
    print(f"live bid/ask  : {bid} / {ask}   spread = {spread}")

    is_exchange = bool(em and "EXCHANGE" in str(em).upper())
    print("\n=== VERDICT ===")
    if is_exchange:
        print("EXCHANGE execution -> order-book account. MAKER edge is POTENTIALLY accessible.")
        print("Next: confirm passive limits can fill at the maker side (no markup) live.")
    else:
        print(f"{em} execution -> DEALER-QUOTE model, NOT an order book.")
        print("Resting BUY_LIMIT/SELL_LIMIT do NOT provide liquidity; when triggered they")
        print("execute at the broker bid/ask = you STILL cross the spread = PERMANENT TAKER.")
        print("snap_ict_maker_rp.py maker edge is INACCESSIBLE on this account.")
        print("-> Pivot to the taker-robust H4 trend-follower bot/challenge_xau.py.")


if __name__ == "__main__":
    main()
