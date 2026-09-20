"""Structured order/deal record keeping -> journal/orders.csv.

One row per order EVENT (open, close, modify, cancel, fill). The CSV is the
audit trail; journal.md stays the narrative log.
"""
import csv
import os
from datetime import datetime, timezone

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "journal", "orders.csv")

FIELDS = ["timestamp_utc", "event", "symbol", "side", "lots", "price",
          "sl", "tp", "risk_usd", "rr", "order_id", "position_id",
          "profit_usd", "balance_after", "notes"]


def append(event: str, **kw) -> None:
    new_file = not os.path.exists(CSV_PATH)
    row = {f: kw.get(f, "") for f in FIELDS}
    row["event"] = event
    row["timestamp_utc"] = kw.get(
        "timestamp_utc",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(row)
