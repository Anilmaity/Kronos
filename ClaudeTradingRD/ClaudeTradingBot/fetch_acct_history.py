"""Fetch full trading history for a MetaApi account via the verified london REST host.

One-off pull for account 5216074f-... using the token the user supplied in chat.
Reuses the endpoint conventions from bot/brokers/metaapi.py (auth-token header,
history-deals/time + history-orders/time). Writes a JSON dump + prints a summary.
"""
import json
import sys
import time
import datetime as dt
from urllib.parse import quote

import requests

BASE = "https://mt-client-api-v1.london.agiliumtrade.ai"
ACCOUNT_ID = "5216074f-3607-4285-967e-1383632f4815"
TOKEN = ("eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJmMzIwMjczMzdhNGE2MjIxM2Q3MTIx"
         "YjFiMGI0ZWE1MiIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2Vt"
         "ZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6"
         "cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVT"
         "RVJfSUQkOjUyMTYwNzRmLTM2MDctNDI4NS05NjdlLTEzODM2MzJmNDgxNSJdfSx7ImlkIjoibWV0"
         "YWFwaS1yZXN0LWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0s"
         "InJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9J"
         "RCQ6NTIxNjA3NGYtMzYwNy00Mjg1LTk2N2UtMTM4MzYzMmY0ODE1Il19XSwiaWdub3JlUmF0ZUxp"
         "bWl0cyI6ZmFsc2UsInRva2VuSWQiOiIyMDIxMDIxMyIsImltcGVyc29uYXRlZCI6ZmFsc2UsInJl"
         "YWxVc2VySWQiOiJmMzIwMjczMzdhNGE2MjIxM2Q3MTIxYjFiMGI0ZWE1MiIsImlhdCI6MTc4MjEw"
         "NzA2MH0.PMyJXX80EilVvETIsGJtDdc7_Et0dyPD9LO5qYXSQ6h1dFpz6x1yhiZgfjIZpRo3m3Bly"
         "c4xs-LB0NFHRxyRJtmjU5Wd9gSQTgpGuunAlbpiHieP50LoDpcshSesc3rg6QQLnkWZKWVrVqgAU5"
         "q_8ytjnMbI5KnmJEVuu0w4X195dfgSU1uVNCWTE6-glxO7DRlhqBdxzbAkkkrJ1qy6VcAlJmkJxG4"
         "GFmbJlkfTqH3M-wqF4xn2Unun3o10Tluh1xhlZu4zgYVKVZ5yKrd8kVx4-UEb1NxnM_wFoit-1M-N"
         "lT1QNTP-47eto3fkBTJ1Yti9NkZFN4x88wPSQxbnfvkl6rWkXA3cPmKcs9wDCP4H2Y_ijMJI7hlHS"
         "aigYZEEcpP905husCVlHWCwUofWVGtKuZt5d4smLB-BpttfEmYdfIc_MjVQ_kMQZLfzDkeCS0UHeZ"
         "AmFUQcvR6J3j9Z5bgWStWxudYP9chSrYYtF7uimE5qoy0X2uT5duOJxMF_xM93rAjA-vPoHlLx_0Z"
         "y71toNM_UPTMlPdHl6wY4aUqjKJOHleOkfdD0vXrGZJmADOXAHVeHaz35bc1yy-3oWA9IAe8DWYpv"
         "ZDvCZkVzk6KoVr3fWt0AeD-SUN-1lU60ne_ICyRQYqENWoB7nhh66BFCEIBrgIYgJfFHAGPiYGs")

H = {"auth-token": TOKEN, "Content-Type": "application/json"}


def get(path, retries=4):
    url = f"{BASE}/users/current/accounts/{ACCOUNT_ID}/{path}"
    last = None
    for _ in range(retries):
        try:
            r = requests.get(url, headers=H, timeout=40)
            if r.status_code in (502, 504):
                last = f"{r.status_code} {r.text[:200]}"
                time.sleep(3)
                continue
            if not r.ok:
                return {"_error": r.status_code, "_body": r.text[:500]}
            return r.json()
        except requests.RequestException as e:
            last = str(e)
            time.sleep(3)
    return {"_error": "exhausted", "_body": last}


def iso(d):
    return quote(d.strftime("%Y-%m-%dT%H:%M:%S.000Z"), safe="")


print("== account-information ==")
info = get("account-information")
print(json.dumps(info, indent=2)[:1500])

start = dt.datetime(2015, 1, 1)
end = dt.datetime.utcnow() + dt.timedelta(days=1)

print("\n== history-deals (2015-01-01 .. now) ==")
deals = get(f"history-deals/time/{iso(start)}/{iso(end)}")
print("type:", type(deals).__name__,
      "count:", len(deals) if isinstance(deals, list) else deals)

print("\n== history-orders (2015-01-01 .. now) ==")
orders = get(f"history-orders/time/{iso(start)}/{iso(end)}")
print("type:", type(orders).__name__,
      "count:", len(orders) if isinstance(orders, list) else orders)

print("\n== open positions ==")
positions = get("positions")
print("count:", len(positions) if isinstance(positions, list) else positions)

dump = {"fetched_utc": dt.datetime.utcnow().isoformat() + "Z",
        "account_id": ACCOUNT_ID,
        "account_information": info,
        "deals": deals, "orders": orders, "positions": positions}
with open("reports/acct_5216074f_history.json", "w", encoding="utf-8") as f:
    json.dump(dump, f, indent=2, default=str)
print("\nSaved -> reports/acct_5216074f_history.json")
