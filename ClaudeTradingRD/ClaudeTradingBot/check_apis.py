"""Verify OANDA and MetaApi connectivity."""
import os, json, requests
from dotenv import load_dotenv

load_dotenv()
OANDA_KEY = os.getenv("OANDA_API_KEY")
META_ID = os.getenv("META_ACCOUNT_ID")
META_TOKEN = os.getenv("META_API_TOKEN")

print("=== OANDA: list accounts (practice) ===")
for host in ["https://api-fxpractice.oanda.com", "https://api-fxtrade.oanda.com"]:
    try:
        r = requests.get(f"{host}/v3/accounts",
                         headers={"Authorization": f"Bearer {OANDA_KEY}"}, timeout=15)
        print(host, r.status_code, r.text[:300])
    except Exception as e:
        print(host, "ERROR", e)

print("\n=== MetaApi: account info (provisioning) ===")
try:
    r = requests.get(
        f"https://mt-provisioning-api-v1.agiliumtrade.agiliumlabs.cloud/users/current/accounts/{META_ID}",
        headers={"auth-token": META_TOKEN}, timeout=20)
    print(r.status_code)
    if r.ok:
        d = r.json()
        print(json.dumps({k: d.get(k) for k in
                          ["_id", "name", "type", "login", "server", "state",
                           "connectionStatus", "region", "reliability", "platform"]}, indent=1))
    else:
        print(r.text[:500])
except Exception as e:
    print("ERROR", e)
