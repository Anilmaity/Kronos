"""Smoke test for s5_engine on the January month file (runs while full download continues)."""
import os

import numpy as np

import s5_engine as eng

path = os.path.join(eng.HERE, "reports", "s5_2026", "xau_s5_2026-01.csv.gz")
df = eng.load_s5(path)
print(f"bars={len(df)} span={df.time.iloc[0]} -> {df.time.iloc[-1]}")
spread = (df.ask_c - df.bid_c)
print(f"spread pts: median={spread.median():.3f} p90={spread.quantile(.9):.3f} max={spread.max():.2f}")

# trivial strategy: buy at first bar at/after 08:00 UTC each day, TP +1.5, SL -1.5, max 1h
hours = df.time.dt.hour.values
days = df.time.dt.date.values
is_0800 = (hours == 8) & (np.roll(hours, 1) != 8)
idx = np.where(is_0800)[0]
intents = [
    eng.OrderIntent(signal_i=int(i), side="buy",
                    tp=float(df.mid_c.iloc[i] + 1.5), sl=float(df.mid_c.iloc[i] - 1.5),
                    max_hold_bars=720, lot=0.10, tag="smoke")
    for i in idx if i + 1 < len(df)
]
fills = eng.simulate(df, intents)
s = eng.stats(df, fills, "smoke_0800_buy")
import json
print(json.dumps(s, indent=2))

# invariants
assert all(f.entry_px >= df.bid_o.iloc[f.entry_i] for f in fills), "long entry below bid?!"
assert all(f.exit_i >= f.entry_i for f in fills)
tp_fills = [f for f in fills if f.exit_reason == "tp"]
sl_fills = [f for f in fills if f.exit_reason == "sl"]
if tp_fills:
    assert all(abs(f.exit_px - f.intent.tp) < 1e-9 for f in tp_fills)
if sl_fills:
    assert all(f.exit_px < f.intent.sl for f in sl_fills), "SL slippage should be adverse for longs"
print("SMOKE OK")
