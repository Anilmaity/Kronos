"""Fetch XAU_USD M1 mid-price candles from OANDA (practice) into a parquet cache.

Usage: python fetch_oanda_m1.py [days]     # default 92
Writes xau_m1_oanda.parquet with columns time/open/high/low/close.
"""

import os
import sys

import pandas as pd
import requests

API_KEY = os.environ.get(
    "OANDA_API_KEY",
    "c17c606a2f01975df287675814550ddf-df0201ce97ccf3deeac8805e58b96def",
)
HOST = "https://api-fxpractice.oanda.com"
OUT = "xau_m1_oanda.parquet"


def fetch(days: int) -> pd.DataFrame:
    end = pd.Timestamp.now("UTC").floor("min")
    cur = end - pd.Timedelta(days=days)
    rows = []
    sess = requests.Session()
    sess.headers["Authorization"] = f"Bearer {API_KEY}"
    while cur < end:
        r = sess.get(
            f"{HOST}/v3/instruments/XAU_USD/candles",
            params={"granularity": "M1", "count": 5000, "price": "M",
                    "from": cur.strftime("%Y-%m-%dT%H:%M:%SZ")},
            timeout=30,
        )
        r.raise_for_status()
        candles = r.json()["candles"]
        if not candles:
            break
        for cd in candles:
            if cd["complete"]:
                m = cd["mid"]
                rows.append((cd["time"], float(m["o"]), float(m["h"]),
                             float(m["l"]), float(m["c"])))
        last = pd.Timestamp(candles[-1]["time"])
        if last <= cur:
            break
        cur = last + pd.Timedelta(minutes=1)
        print(f"\r{cur.date()}  {len(rows):,} bars", end="", flush=True)
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.drop_duplicates("time").sort_values("time").reset_index(drop=True)


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 92
    df = fetch(days)
    df.to_parquet(OUT)
    print(f"\nsaved {OUT}: {len(df):,} bars  {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
