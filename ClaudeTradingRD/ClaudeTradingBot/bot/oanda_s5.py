"""OANDA practice S5 (5-second) bid/ask history fetcher + loader.

Stores compact monthly .npz files under reports/s5/ so the microstructure
research loop reads real bid/ask bars, not a fixed-spread assumption.

Schema per .npz (one file per calendar month, UTC):
    ts   int64    epoch seconds, strictly increasing
    bo bh bl bc   float32  BID  open/high/low/close
    ao ah al ac   float32  ASK  open/high/low/close
    vol  int32    tick volume

CLI:
    python bot/oanda_s5.py fetch 2025-01 2026-06     # inclusive month range
    python bot/oanda_s5.py status                     # what's cached
"""
import os
import sys
import time
import datetime as dt
import numpy as np
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S5_DIR = os.path.join(ROOT, "reports", "s5")
BASE = "https://api-fxpractice.oanda.com"
INSTRUMENT = "XAU_USD"


def _key():
    # read OANDA_API_KEY without dotenv's find-frame quirk
    k = os.getenv("OANDA_API_KEY")
    if k:
        return k
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8", errors="ignore"):
        if line.startswith("OANDA_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OANDA_API_KEY not found")


HEADERS = {"Authorization": f"Bearer {_key()}"}


def _iso(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


def _fetch_window(frm: dt.datetime, to: dt.datetime):
    """Yield complete S5 candles in [frm, to) via from/to pagination (<=5000/req)."""
    cur = frm
    while cur < to:
        r = requests.get(
            f"{BASE}/v3/instruments/{INSTRUMENT}/candles",
            headers=HEADERS,
            params={"granularity": "S5", "price": "BA", "count": 5000,
                    "from": _iso(cur), "includeFirst": True},
            timeout=60,
        )
        if r.status_code == 429:  # rate limited
            time.sleep(2.0)
            continue
        if r.status_code == 400:  # from at/after last available candle -> done
            return
        r.raise_for_status()
        cs = r.json()["candles"]
        if not cs:
            break
        last_t = None
        for c in cs:
            t = dt.datetime.fromisoformat(c["time"].replace("Z", "+00:00")).replace(tzinfo=None)
            if t >= to:
                return
            last_t = t
            if not c["complete"]:
                continue
            yield t, c["bid"], c["ask"], c["volume"]
        if last_t is None:
            break
        nxt = last_t + dt.timedelta(seconds=5)
        if nxt <= cur:
            nxt = cur + dt.timedelta(seconds=5)
        cur = nxt
        time.sleep(0.05)


def fetch_month(year: int, month: int, overwrite=False) -> str:
    os.makedirs(S5_DIR, exist_ok=True)
    path = os.path.join(S5_DIR, f"xau_s5_{year:04d}-{month:02d}.npz")
    if os.path.exists(path) and not overwrite:
        return path + " (cached)"
    frm = dt.datetime(year, month, 1)
    to = dt.datetime(year + (month == 12), (month % 12) + 1, 1)
    now = dt.datetime.utcnow() - dt.timedelta(minutes=2)  # avoid incomplete tail
    if to > now:
        to = now
    ts, bo, bh, bl, bc, ao, ah, al, ac, vol = ([] for _ in range(10))
    n = 0
    for t, bid, ask, v in _fetch_window(frm, to):
        ts.append(int(t.timestamp()))
        bo.append(bid["o"]); bh.append(bid["h"]); bl.append(bid["l"]); bc.append(bid["c"])
        ao.append(ask["o"]); ah.append(ask["h"]); al.append(ask["l"]); ac.append(ask["c"])
        vol.append(v)
        n += 1
    if n == 0:
        return path + " (EMPTY)"
    ts = np.asarray(ts, np.int64)
    order = np.argsort(ts, kind="stable")
    ts = ts[order]
    keep = np.concatenate(([True], np.diff(ts) > 0))  # drop dup timestamps
    arrs = {"ts": ts[keep]}
    for nm, src, ty in [("bo", bo, np.float32), ("bh", bh, np.float32),
                        ("bl", bl, np.float32), ("bc", bc, np.float32),
                        ("ao", ao, np.float32), ("ah", ah, np.float32),
                        ("al", al, np.float32), ("ac", ac, np.float32),
                        ("vol", vol, np.int32)]:
        arrs[nm] = np.asarray(src, ty)[order][keep]
    np.savez_compressed(path, **arrs)
    return f"{path}  ({len(arrs['ts']):,} bars)"


def _months(a: str, b: str):
    ya, ma = map(int, a.split("-")); yb, mb = map(int, b.split("-"))
    y, m = ya, ma
    while (y, m) <= (yb, mb):
        yield y, m
        y, m = (y + (m == 12), (m % 12) + 1)


def load(a: str, b: str):
    """Load months [a..b] inclusive ('YYYY-MM') into one dict of numpy arrays."""
    parts = {k: [] for k in ["ts", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "vol"]}
    for y, m in _months(a, b):
        p = os.path.join(S5_DIR, f"xau_s5_{y:04d}-{m:02d}.npz")
        if not os.path.exists(p):
            continue
        d = np.load(p)
        for k in parts:
            parts[k].append(d[k])
    if not parts["ts"]:
        raise FileNotFoundError(f"no s5 data cached in {a}..{b} ({S5_DIR})")
    return {k: np.concatenate(v) for k, v in parts.items()}


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "status":
        os.makedirs(S5_DIR, exist_ok=True)
        files = sorted(f for f in os.listdir(S5_DIR) if f.endswith(".npz"))
        tot = 0
        for f in files:
            d = np.load(os.path.join(S5_DIR, f))
            n = len(d["ts"]); tot += n
            print(f"{f}  {n:,} bars")
        print(f"TOTAL {tot:,} bars across {len(files)} months")
    elif len(sys.argv) >= 3 and sys.argv[1] == "fetch":
        a, b = sys.argv[2], sys.argv[3]
        for y, m in _months(a, b):
            t0 = time.time()
            res = fetch_month(y, m)
            print(f"{y}-{m:02d}: {res}   [{time.time()-t0:.0f}s]", flush=True)
    else:
        print(__doc__)
