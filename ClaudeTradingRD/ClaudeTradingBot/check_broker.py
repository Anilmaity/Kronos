"""Smoke test for the broker layer. Usage: python check_broker.py [mt5|metaapi]"""
import os
import sys

if len(sys.argv) > 1:
    os.environ["BROKER"] = sys.argv[1]

from bot import broker
from bot.brokers import get_broker

b = get_broker()
print("backend:", b.name)

if b.name == "metaapi":
    print("url ok:", b._url("positions").startswith(
        "https://mt-client-api-v1.london.agiliumtrade.ai"))

try:
    info = broker.account_information()
    print("account:", {k: info.get(k) for k in
                       ("login", "server", "broker", "currency", "balance",
                        "equity", "leverage", "tradeAllowed")})
    print("price:", broker.symbol_price())
    print("positions:", broker.positions())
    print("pending:", broker.pending_orders())
    print("OK")
except Exception as e:
    print("LIVE CHECK FAILED:", e)
    sys.exit(1)
