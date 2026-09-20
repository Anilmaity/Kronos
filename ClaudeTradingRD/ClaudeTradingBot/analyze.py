"""Multi-timeframe XAUUSD analysis snapshot."""
import json
from bot import data, analysis

price = data.current_price()
print("PRICE:", json.dumps(price))

tfs = {"D": 120, "H4": 180, "H1": 200, "M15": 200}
cache = {}
for tf, count in tfs.items():
    candles = [c for c in data.candles(tf, count) if c["complete"]]
    cache[tf] = candles
    print(f"\n--- {tf} ---")
    print(json.dumps(analysis.summarize(tf, candles)))

# Key levels
pd = analysis.day_bounds(cache["H1"], 1)
pd2 = analysis.day_bounds(cache["H1"], 2)
print("\nPRIOR DAY:", json.dumps(pd))
print("DAY BEFORE:", json.dumps(pd2))

wk = cache["D"][-5:]
print("WEEK RANGE (5d):", round(max(c['h'] for c in wk), 2), "/",
      round(min(c['l'] for c in wk), 2))

# Unfilled FVGs near price (H1 & H4)
for tf in ("H4", "H1"):
    gaps = analysis.fair_value_gaps(cache[tf], min_size=1.0)
    open_gaps = analysis.unfilled_gaps(cache[tf], gaps, price["mid"])
    near = sorted(open_gaps, key=lambda g: g["dist"])[:4]
    print(f"{tf} UNFILLED FVGs (nearest):", json.dumps(near))

# Recent candles for context
print("\nLAST 6 H1:", json.dumps([{k: c[k] for k in ('time', 'o', 'h', 'l', 'c')}
                                   for c in cache["H1"][-6:]]))
print("\nLAST 10 D:", json.dumps([{k: c[k] for k in ('time', 'o', 'h', 'l', 'c')}
                                   for c in cache["D"][-10:]]))
