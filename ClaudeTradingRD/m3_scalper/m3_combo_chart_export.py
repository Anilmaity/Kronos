"""Export chart payload for the M3 FVG+OB wide-hours (1-15 UTC, no veto) config.

Window: 2026-07-01 .. 2026-07-23. Payload: M3 candles, raw signal zones
(FVG bull/bear, OB bull/bear), simulated trades (entry/exit markers, pts),
per the harness config: dispm 1.0, retrace 12, TP 1.5R, cap 1.5xATR, cost 0.45.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRATCH = Path(__file__).parent
sys.path.insert(0, str(SCRATCH))

from s93_struct_validate import load  # noqa: E402
from s93_ob_validate import run_combo  # noqa: E402
from optimize_manager_strategies import atr_np  # noqa: E402

A = pd.Timestamp("2026-07-01", tz="UTC")
B = pd.Timestamp("2026-07-23 05:00", tz="UTC")
WIDE = tuple(range(1, 16))

m1 = load("1m")
m3_all = (m1.set_index("time").resample("3min")
          .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
          .dropna().reset_index())

mask = (m3_all["time"] >= A - pd.Timedelta(hours=6)) & (m3_all["time"] <= B)
m3 = m3_all[mask].reset_index(drop=True)

# trades from the exact harness config (run on the full frame for warm ATR,
# then clipped to the window)
# WORKING SPEC v2 (user iteration, 2026-07-23): FVG + OB(disp0.5/break3/edge)
# + RSI3-momentum 85/15 + EMA20/200 direction gate, wide hours 1-15 UTC,
# max_concurrent=1. Supersedes the mc=5 lock. Measured 18mo @0.45pt:
# 18.0 tr/day, train PF 1.19 (+1,002pts, 66% pos weeks) / test PF 1.34
# (+2,030pts, 80% pos weeks); @0.80pt train 0.90 — stress-train still short.
trades_all, tags_all = run_combo(m3_all, models=("fvg", "ob", "rsi"),
                                 hours=WIDE, cost=0.45, struct=None,
                                 dispm=0.5, ob_break=3, ob_entry="edge",
                                 rsi_n=3, rsi_ob=85, rsi_os=15,
                                 rsi_mode="momentum", max_concurrent=1,
                                 ema_filter=True)
trades = [(t, g) for t, g in zip(trades_all, tags_all)
          if A <= t.t_entry <= B]

# raw signal zones in the window
h = m3["high"].to_numpy(float)
l = m3["low"].to_numpy(float)
c = m3["close"].to_numpy(float)
o = m3["open"].to_numpy(float)
a = atr_np(h, l, c, 14)
hr = m3["time"].dt.hour.to_numpy()
hi5 = pd.Series(h).rolling(5).max().to_numpy()
lo5 = pd.Series(l).rolling(5).min().to_numpy()
ts = (m3["time"].astype("int64") // 10**9).to_numpy()

zones = []
for k in range(26, len(c)):
    if hr[k] not in WIDE or not (a[k] > 0) or m3["time"].iloc[k] < A:
        continue
    if l[k] > h[k - 2] and 0.3 * a[k] <= (l[k] - h[k - 2]) <= 1.5 * a[k]:
        zones.append({"model": "fvg", "side": 1,
                      "from": int(ts[k - 2]), "to": int(ts[min(k + 12, len(c) - 1)]),
                      "high": round(l[k], 2), "low": round(h[k - 2], 2)})
    elif h[k] < l[k - 2] and 0.3 * a[k] <= (l[k - 2] - h[k]) <= 1.5 * a[k]:
        zones.append({"model": "fvg", "side": -1,
                      "from": int(ts[k - 2]), "to": int(ts[min(k + 12, len(c) - 1)]),
                      "high": round(l[k - 2], 2), "low": round(h[k], 2)})
    else:
        body = c[k] - o[k]
        if c[k] > hi5[k - 1] and body >= 1.0 * a[k]:
            for j in range(k - 1, k - 11, -1):
                if c[j] < o[j]:
                    if abs(o[j] - c[j]) <= 1.5 * a[k]:
                        zones.append({"model": "ob", "side": 1,
                                      "from": int(ts[j]), "to": int(ts[min(k + 12, len(c) - 1)]),
                                      "high": round(o[j], 2), "low": round(c[j], 2)})
                    break
        elif c[k] < lo5[k - 1] and -body >= 1.0 * a[k]:
            for j in range(k - 1, k - 11, -1):
                if c[j] > o[j]:
                    if abs(c[j] - o[j]) <= 1.5 * a[k]:
                        zones.append({"model": "ob", "side": -1,
                                      "from": int(ts[j]), "to": int(ts[min(k + 12, len(c) - 1)]),
                                      "high": round(c[j], 2), "low": round(o[j], 2)})
                    break

candles = [{"time": int(ts[i]), "open": round(float(o[i]), 2),
            "high": round(float(h[i]), 2), "low": round(float(l[i]), 2),
            "close": round(float(c[i]), 2)} for i in range(len(m3))]

markers = []
wins = 0
net = 0.0
for t, g in trades:
    win = t.pnl > 0
    wins += win
    net += t.pnl
    mcolor = {"fvg": "#2196F3", "ob": "#ba68c8", "rsi": "#ff9800"}[g]
    markers.append({"time": int(t.t_entry.timestamp()),
                    "position": "belowBar" if t.side > 0 else "aboveBar",
                    "shape": "arrowUp" if t.side > 0 else "arrowDown",
                    "color": mcolor,
                    "text": f"{g.upper()} {t.entry:.1f}"})
    markers.append({"time": int(t.t_exit.timestamp()),
                    "position": "aboveBar" if t.side > 0 else "belowBar",
                    "shape": "circle",
                    "color": "#4CAF50" if win else "#F44336",
                    "text": f"{t.outcome} {t.pnl:+.1f}"})
markers.sort(key=lambda m: m["time"])

payload = {
    "symbol": "XAUUSD", "interval": "M3",
    "title": (f"FVG+OB+RSI M3 wide-hours 1-15 UTC (no veto) — Jul 1-23 2026 | "
              f"{len(trades)} trades, {wins}W-{len(trades)-wins}L, "
              f"net {net:+.0f}pts @0.45 | blue=FVG, purple=OB, orange=RSI"),
    "candles": candles, "fvgs": [], "markers": markers, "zones": zones,
}
(SCRATCH / "m3_combo_chart_data.json").write_text(json.dumps(payload), encoding="utf-8")
print(f"candles={len(candles)} zones={len(zones)} trades={len(trades)} "
      f"({wins}W) net={net:+.0f}pts")
