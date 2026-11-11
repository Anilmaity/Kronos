"""XM GOLD deal price vs OANDA XAU_USD quote at the same instant -> basis.json.

Run from anywhere:  ../../../.venv/bin/python 01_basis.py
A BUY deal fills at XM's ask, a SELL deal at XM's bid, so each side is measured against
the same OANDA side. Reference = linear interpolation open->close inside the 5-second
bar that contains the deal timestamp.
Excluded from the estimate: close-by deals (their "price" is the opposite leg's open price,
not a market price) and TP / stop-out fills (clustered in news seconds where a 5 s bar spans
10-30 USD, so the within-bar position dominates the error).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

d = pd.read_csv(ROOT / "deals.csv")
d["time"] = pd.to_datetime(d["time"], utc=True, format="ISO8601")
s5 = pd.read_parquet(ROOT / "xau_s5_2026-11-03_now_ba.parquet").set_index("time")
td = d[d.symbol.notna()].reset_index(drop=True)
td["side"] = np.where(td.type == "DEAL_TYPE_BUY", "ask", "bid")


def oanda_ref(times, side, shift_s=0.0):
    """OANDA same-side price at times+shift (interpolated inside the containing S5 bar)."""
    tt = times + pd.Timedelta(seconds=shift_s)
    k = tt.dt.floor("5s")
    b = s5.iloc[s5.index.searchsorted(k, side="right") - 1]
    fresh = k.values == b.index.values  # False -> no bar for that 5 s (no ticks): use last close
    frac = ((tt - k).dt.total_seconds() / 5).values
    ask = side.values == "ask"
    o = np.where(ask, b.ask_open, b.bid_open)
    c = np.where(ask, b.ask_close, b.bid_close)
    rng = np.where(ask, b.ask_high - b.ask_low, b.bid_high - b.bid_low)
    return np.where(fresh, o + (c - o) * frac, c), rng


m = td[(td.reason == "DEAL_REASON_MOBILE") & (td.entryType != "DEAL_ENTRY_OUT_BY")].copy()
print(f"trade deals {len(td)}; used for basis (manual market fills, no close-by) n={len(m)}")

print("\nclock check - dispersion of (deal - OANDA) if the deal clock were shifted by s seconds:")
for sh in (-10, -5, -2, -1, 0, 1, 2, 5, 10):
    e = m.price.values - oanda_ref(m.time, m.side, sh)[0]
    print(f"  shift {sh:+3d}s  median {np.median(e):+.3f}  MAD {np.median(np.abs(e - np.median(e))):.3f}  rmse {np.sqrt((e**2).mean()):.3f}")

ref, rng = oanda_ref(m.time, m.side)
m["err"], m["bar_range"], m["day"] = m.price.values - ref, rng, m.time.dt.date
print("\nbasis by side, all manual fills (USD/oz):")
print(m.groupby("side").err.agg(["count", "median", "mean", "std"]).round(3))
print("\nbasis by side, calm bars only (5 s range <= 0.25):")
print(m[m.bar_range <= 0.25].groupby("side").err.agg(["count", "median", "mean", "std"]).round(3))
print("\nbasis by day and side (median):")
print(m.pivot_table(index="day", columns="side", values="err", aggfunc=["count", "median"]).round(3))

ask_b = float(m[m.side == "ask"].err.median())
bid_b = float(m[m.side == "bid"].err.median())
win = s5.loc["2026-11-04":]
oanda_spread = float((win.ask_close - win.bid_close).median())
out = dict(
    ask_basis=round(ask_b, 4), bid_basis=round(bid_b, 4), mid_basis=round((ask_b + bid_b) / 2, 4),
    n_ask=int((m.side == "ask").sum()), n_bid=int((m.side == "bid").sum()),
    oanda_median_spread=round(oanda_spread, 3), xm_implied_median_spread=round(oanda_spread + ask_b - bid_b, 3),
    note="XM = OANDA + basis, per side; medians over manual market fills 2026-11-04..11-11",
)
(HERE / "basis.json").write_text(json.dumps(out, indent=2))
print("\n", json.dumps(out, indent=2))
