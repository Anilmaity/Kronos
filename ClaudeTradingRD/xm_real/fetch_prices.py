"""Fetch OANDA XAU_USD candles for the XM Real study. Usage: python fetch_prices.py"""
import sys
import pandas as pd, requests
sys.path.insert(0, "..")
from fetch_oanda_m1 import API_KEY, HOST

def fetch(gran, start, end, price):
    s = requests.Session(); s.headers["Authorization"] = f"Bearer {API_KEY}"
    cur, rows = pd.Timestamp(start, tz="UTC"), []
    end = pd.Timestamp(end, tz="UTC")
    while cur < end:
        r = s.get(f"{HOST}/v3/instruments/XAU_USD/candles", timeout=60,
                  params={"granularity": gran, "count": 5000, "price": price, "from": cur.isoformat()})
        r.raise_for_status()
        cs = [c for c in r.json()["candles"] if c["complete"]]
        if not cs: break
        for c in cs:
            row = {"time": c["time"], "volume": c["volume"]}
            for k, name in (("mid", ""), ("bid", "bid_"), ("ask", "ask_")):
                if k in c:
                    for f, n in zip("ohlc", ("open", "high", "low", "close")):
                        row[name + n] = float(c[k][f])
            rows.append(row)
        nxt = pd.Timestamp(cs[-1]["time"]) + pd.Timedelta(seconds=1)
        if nxt <= cur: break
        cur = nxt
    df = pd.DataFrame(rows); df["time"] = pd.to_datetime(df["time"], utc=True)
    return df[df.time < end].drop_duplicates("time").reset_index(drop=True)

if __name__ == "__main__":
    now = pd.Timestamp.now("UTC").floor("min").tz_localize(None)
    m1 = fetch("M1", "2026-07-16", now, "MBA"); m1.to_parquet("xau_m1_2026-07-16_now_mba.parquet"); print("M1", m1.shape, m1.time.min(), m1.time.max())
    s5 = fetch("S5", "2026-11-03", now, "BA"); s5.to_parquet("xau_s5_2026-11-03_now_ba.parquet"); print("S5", s5.shape, s5.time.min(), s5.time.max())
