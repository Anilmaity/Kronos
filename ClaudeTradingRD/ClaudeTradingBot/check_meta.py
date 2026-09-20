"""Probe regional MetaApi client hosts for our account."""
import os, requests
from dotenv import load_dotenv

load_dotenv()
META_ID = os.getenv("META_ACCOUNT_ID")
H = {"auth-token": os.getenv("META_API_TOKEN")}

regions = ["vint-hill", "new-york", "london", "singapore", "tokyo", "frankfurt",
           "mumbai", "sydney", "sao-paulo"]
for region in regions:
    for domain in ["agiliumtrade.agiliumtrade.ai", "agiliumtrade.ai"]:
        url = (f"https://mt-client-api-v1.{region}.{domain}"
               f"/users/current/accounts/{META_ID}/account-information")
        try:
            r = requests.get(url, headers=H, timeout=20)
            print(region, domain, r.status_code, r.text[:300])
            if r.ok:
                raise SystemExit
        except requests.RequestException as e:
            print(region, domain, "ERR", str(e)[:90])
