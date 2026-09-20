"""Quick snapshot: account, positions, symbol spec, prices."""
import json
from bot import broker, data

info = broker.account_information()
print("ACCOUNT:", json.dumps({k: info.get(k) for k in
      ["balance", "equity", "margin", "freeMargin", "leverage", "currency"]}))
pos = broker.positions()
print("POSITIONS:", json.dumps(pos, default=str))
orders = broker.pending_orders()
print("PENDING:", json.dumps(orders, default=str))
spec = broker.symbol_spec()
print("SPEC:", json.dumps({k: spec.get(k) for k in
      ["symbol", "minVolume", "maxVolume", "volumeStep", "contractSize",
       "digits", "tickSize", "tickValue", "stopsLevel", "tradeMode"]}))
mp = broker.symbol_price()
print("MT5 PRICE:", json.dumps({k: mp.get(k) for k in ["bid", "ask", "time"]}, default=str))
op = data.current_price()
print("OANDA PRICE:", json.dumps(op))
