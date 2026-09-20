"""Fetch XAU_USD candles from OANDA practice over a date range, paginated.

Used to (a) validate the mobile-scalp fills against real price and (b) build the
backtest dataset. Writes CSV: time,o,h,l,c,volume.
"""
import os
import sys
import time
import csv
import datetime as dt

import requests
from dotenv import load_dotenv

load_dotenv()
BASE = "https://api-fxpractice.oanda.com"
H = {"Authorization": f"Bearer {os.getenv('OANDA_API_KEY')}"}
INSTR = "XAU_USD"


def fetch(start: dt.datetime, end: dt.datetime, gran="M1", out=None):
    rows = []
    cur = start
    step_max = 4900
    while cur < end:
        r = requests.get(
            f"{BASE}/v3/instruments/{INSTR}/candles",
            headers=H,
            params={"granularity": gran, "from": cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "count": step_max, "price": "M"},
            timeout=40,
        )
        if not r.ok:
            print("ERR", r.status_code, r.text[:200]); break
        cs = r.json()["candles"]
        if not cs:
            break
        last_t = None
        for c in cs:
            t = c["time"]
            tt = dt.datetime.fromisoformat(t.replace("Z", "+00:00")).replace(tzinfo=None)
            if tt >= end:
                break
            if not c["complete"]:
                continue
            m = c["mid"]
            rows.append([tt.strftime("%Y-%m-%d %H:%M:%S"), float(m["o"]), float(m["h"]),
                         float(m["l"]), float(m["c"]), c["volume"]])
            last_t = tt
        if last_t is None or last_t <= cur:
            cur = cur + dt.timedelta(minutes=step_max)
        else:
            cur = last_t + dt.timedelta(seconds=1)
        time.sleep(0.15)
    if out:
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["time", "o", "h", "l", "c", "volume"]); w.writerows(rows)
    return rows


if __name__ == "__main__":
    name = sys.argv[1]
    start = dt.datetime.fromisoformat(sys.argv[2])
    end = dt.datetime.fromisoformat(sys.argv[3])
    gran = sys.argv[4] if len(sys.argv) > 4 else "M1"
    rows = fetch(start, end, gran, out=name)
    print(f"{name}: {len(rows)} candles {gran}  {rows[0][0] if rows else '-'} .. {rows[-1][0] if rows else '-'}")
