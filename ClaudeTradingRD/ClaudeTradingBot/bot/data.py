"""OANDA practice API: XAU_USD candles and live pricing."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api-fxpractice.oanda.com"
HEADERS = {"Authorization": f"Bearer {os.getenv('OANDA_API_KEY')}"}
OANDA_ACCOUNT = "101-004-37228564-001"
INSTRUMENT = "XAU_USD"


def candles(granularity: str = "H1", count: int = 200,
            instrument: str = INSTRUMENT, price: str = "M") -> list:
    """granularity: M5, M15, M30, H1, H4, D, W. Returns list of dicts with
    time, o, h, l, c, volume, complete."""
    r = requests.get(
        f"{BASE}/v3/instruments/{instrument}/candles",
        headers=HEADERS,
        params={"granularity": granularity, "count": count, "price": price},
        timeout=30,
    )
    r.raise_for_status()
    out = []
    for c in r.json()["candles"]:
        mid = c["mid"]
        out.append({
            "time": c["time"],
            "o": float(mid["o"]), "h": float(mid["h"]),
            "l": float(mid["l"]), "c": float(mid["c"]),
            "volume": c["volume"], "complete": c["complete"],
        })
    return out


def current_price(instrument: str = INSTRUMENT) -> dict:
    r = requests.get(
        f"{BASE}/v3/accounts/{OANDA_ACCOUNT}/pricing",
        headers=HEADERS, params={"instruments": instrument}, timeout=30,
    )
    r.raise_for_status()
    p = r.json()["prices"][0]
    bid = float(p["bids"][0]["price"])
    ask = float(p["asks"][0]["price"])
    return {"bid": bid, "ask": ask, "mid": round((bid + ask) / 2, 2), "time": p["time"]}
