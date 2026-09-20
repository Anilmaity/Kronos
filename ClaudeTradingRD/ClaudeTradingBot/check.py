"""Per-wake snapshot: account, position state, price vs plan zones, recent M15/H1."""
import json
from bot import broker, data, analysis

LONG_ZONE = (4107.76, 4131.46)   # H1 bullish FVG
SHORT_ZONE = (4219.2, 4249.96)   # H4 bearish FVG
PDH = 4228.5
EQ = 4193.8

info = broker.account_information()
print("ACCOUNT:", json.dumps({k: info.get(k) for k in ["balance", "equity", "margin", "freeMargin"]}))
pos = broker.positions()
if pos:
    print("POSITIONS:", json.dumps([{k: p.get(k) for k in
        ["id", "type", "volume", "openPrice", "stopLoss", "takeProfit", "profit", "time"]}
        for p in pos], default=str))
else:
    print("POSITIONS: flat")
orders = broker.pending_orders()
print("PENDING:", json.dumps(orders, default=str) if orders else "PENDING: none")

p = data.current_price()
mid = p["mid"]
print(f"PRICE: {mid} (bid {p['bid']} ask {p['ask']}) at {p['time'][:19]}")

flags = []
if LONG_ZONE[0] <= mid <= LONG_ZONE[1]:
    flags.append("IN LONG ZONE (H1 bull FVG)")
if SHORT_ZONE[0] <= mid <= SHORT_ZONE[1]:
    flags.append("IN SHORT ZONE (H4 bear FVG)")
flags.append("above EQ" if mid > EQ else "below EQ")
m15 = [c for c in data.candles("M15", 30) if c["complete"]]
h1 = [c for c in data.candles("H1", 30) if c["complete"]]
if max(c["h"] for c in m15) > PDH or mid > PDH:
    flags.append(f"PDH {PDH} SWEPT")
print("FLAGS:", " | ".join(flags))
print("M15 bias:", analysis.structure_bias(m15), "| H1 bias:", analysis.structure_bias(h1),
      "| M15 ATR:", analysis.atr(m15))
print("LAST 8 M15:", json.dumps([{k: c[k] for k in ("time", "o", "h", "l", "c")}
                                  for c in m15[-8:]]))
