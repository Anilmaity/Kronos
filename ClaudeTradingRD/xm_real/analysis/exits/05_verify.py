"""Step 5 - independent recomputation of headline numbers from the raw files, with plain bar-by-bar loops
(no code shared with common.Quotes / 03's searchsorted simulator). Fails loudly on a mismatch.
Run: python 05_verify.py
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
XM = HERE.parents[1]
b = json.load(open(HERE / "basis.json"))
s5 = pd.read_parquet(XM / "xau_s5_2026-11-03_now_ba.parquet")
T = s5.time.dt.tz_convert(None).values.astype("datetime64[ns]").astype("int64").tolist()
BID = {k: (s5[f"bid_{k}"] + b["bid"]).tolist() for k in ("open", "high", "low", "close")}
ASK = {k: (s5[f"ask_{k}"] + b["ask"]).tolist() for k in ("open", "high", "low", "close")}
tr = pd.read_csv(XM / "trades.csv")
for c in ("open_time", "close_time"):
    tr[c] = pd.to_datetime(tr[c], utc=True, format="ISO8601").dt.tz_convert(None).values.astype("datetime64[ns]").astype("int64")
tr = tr.sort_values("open_time").reset_index(drop=True)
ex = pd.read_csv(HERE / "trade_excursions.csv")
allr = pd.read_csv(HERE / "results" / "cf_all.csv")
grid = pd.read_csv(HERE / "results" / "cf_grid.csv")
SLIP = 0.30


def first_bar(t):
    lo, hi = 0, len(T)
    while lo < hi:                      # first bar opening at/after t
        mid = (lo + hi) // 2
        if T[mid] < t:
            lo = mid + 1
        else:
            hi = mid
    return lo


def fixed(side, entry, t0, tp, sl):
    """TP/SL bar-by-bar; same rules as the report (stop first in a tie, gap -> bar open, slip on stops, MTM at end)."""
    i = first_bar(t0)
    for j in range(i, len(T)):
        if side == "BUY":
            o, h, l = BID["open"][j] - entry, BID["high"][j] - entry, BID["low"][j] - entry
        else:
            o, h, l = entry - ASK["open"][j], entry - ASK["low"][j], entry - ASK["high"][j]
        if l <= -sl:
            return min(-sl, o) - SLIP
        if h >= tp:
            return tp
    return (BID["close"][-1] - entry) if side == "BUY" else (entry - ASK["close"][-1])


# 1) grid cell TP5 / SL10 and TP4 / SL25, all 178
for tp, sl in ((5.0, 10.0), (4.0, 25.0)):
    tot = sum(fixed(r.side, r.entry, r.open_time, tp, sl) for r in tr.itertuples())
    ref = grid[(grid.subset == "ALL") & (grid.tp == tp) & (grid.sl == sl)].total_pts.iloc[0]
    print(f"grid TP{tp:g}/SL{sl:g}: loop {tot:.1f} vs pipeline {ref:.1f}")
    assert abs(tot - ref) < 0.11

# 2) MAE during the real hold, bar-by-bar, for every non-close-by position
worst = 0.0
for r, e in zip(tr.itertuples(), ex.itertuples()):
    if e.closeby:
        continue
    mae = r.pts
    for j in range(first_bar(r.open_time), len(T)):
        if T[j] + 5 * 10**9 > r.close_time:
            break
        mae = min(mae, (BID["low"][j] - r.entry) if r.side == "BUY" else (r.entry - ASK["high"][j]))
    worst = max(worst, abs(mae - e.mae_pts))
print(f"MAE of 170 positions: max |loop - csv| = {worst:.4f} pts")
assert worst < 0.002

# 3) totals straight from the broker ledger
pts_once = (tr.profit / (tr.volume * 100)).sum()
print(f"realised points, each close-by pair once: {pts_once:.2f}; sum of profit ${tr.profit.sum():.2f}; net ${tr.net.sum():.2f}")
assert abs(pts_once - allr[(allr.family == 'actual') & (allr.subset == 'ALL')].total_pts.iloc[0]) < 0.06
print("verify OK")
