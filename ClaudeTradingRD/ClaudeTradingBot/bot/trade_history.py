"""Parse journal/orders.csv into per-symbol trade records for the dashboard.

A "trade taken by this app" = one position the bot opened (and optionally closed).
The CSV is an event log (one row per order event); this module reconstructs whole
trades from it so the dashboard can show a Gold / BTC order-history report.

Pairing rule (robust to the messy 2026-06-11 backfill rows where scale-in entries
are mislabeled `backfill_close`): group rows by position_id, order by time. The
EARLIEST row is the entry; later rows are exits (event contains "close"),
cancels (event contains "cancel") or modifies. This is pure + file-only — no
broker — so the report stays available even when MT5 is offline.
"""
import csv
import os

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "journal", "orders.csv")

SYMBOLS = ("XAUUSD", "BTCUSDT")


def _f(x):
    """CSV cell -> float or None (blank / unparseable -> None)."""
    if x is None:
        return None
    x = str(x).strip()
    if x == "":
        return None
    try:
        return float(x)
    except ValueError:
        return None


def _blank_summary():
    return {"closed": 0, "wins": 0, "losses": 0, "win_rate": None,
            "net_pnl": 0.0, "gross_win": 0.0, "gross_loss": 0.0,
            "open": 0, "cancelled": 0}


def _build_trade(rows):
    """rows = all CSV rows for one position_id, time-sorted. -> trade dict."""
    entry = rows[0]
    rest = rows[1:]

    closes = [r for r in rest if "close" in r["event"]]
    cancels = [r for r in rest if "cancel" in r["event"]]

    if closes:
        status = "closed"
        exit_row = closes[-1]
        profit = sum(_f(r.get("profit_usd")) or 0.0 for r in closes)
        exit_price = _f(exit_row.get("price"))
        exit_time = exit_row.get("timestamp_utc")
        balance_after = _f(exit_row.get("balance_after"))
    elif cancels:
        status = "cancelled"
        exit_row = cancels[-1]
        profit = None
        exit_price = None
        exit_time = exit_row.get("timestamp_utc")
        balance_after = _f(exit_row.get("balance_after"))
    else:
        status = "open"
        profit = None
        exit_price = None
        exit_time = None
        balance_after = None

    # Intent: prefer the entry's note; fall back to any non-empty note on the trade.
    notes = (entry.get("notes") or "").strip()
    if not notes:
        for r in rest:
            n = (r.get("notes") or "").strip()
            if n:
                notes = n
                break

    return {
        "position_id": entry.get("position_id") or entry.get("order_id"),
        "symbol": entry.get("symbol"),
        "side": (entry.get("side") or "").strip().lower(),
        "lots": _f(entry.get("lots")),
        "entry_time": entry.get("timestamp_utc"),
        "entry_price": _f(entry.get("price")),
        "sl": _f(entry.get("sl")),
        "tp": _f(entry.get("tp")),
        "risk_usd": _f(entry.get("risk_usd")),
        "rr": _f(entry.get("rr")),
        "exit_time": exit_time,
        "exit_price": exit_price,
        "profit_usd": profit,
        "balance_after": balance_after,
        "status": status,
        "notes": notes,
    }


def load_trades(csv_path=None):
    """Return {symbol: [trade, ...newest-first], summary: {symbol/all: {...}}}."""
    csv_path = csv_path or CSV_PATH
    out = {s: [] for s in SYMBOLS}
    out["summary"] = {s: _blank_summary() for s in SYMBOLS}
    out["summary"]["all"] = _blank_summary()

    if not os.path.exists(csv_path):
        return out

    # Group event rows by position_id, preserving file order as a stable tiebreak.
    groups = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            pid = (row.get("position_id") or "").strip()
            if not pid:
                continue  # e.g. a `modify` row with no position_id — nothing to pair
            row["_seq"] = i
            groups.setdefault(pid, []).append(row)

    trades = []
    for pid, rows in groups.items():
        rows.sort(key=lambda r: (r.get("timestamp_utc") or "", r["_seq"]))
        sym = next((r.get("symbol") for r in rows if r.get("symbol")), None)
        if sym not in SYMBOLS:
            continue
        trades.append(_build_trade(rows))

    # Newest entry first, per symbol.
    for sym in SYMBOLS:
        out[sym] = sorted([t for t in trades if t["symbol"] == sym],
                          key=lambda t: t.get("entry_time") or "", reverse=True)

    # Summaries (win/loss computed over CLOSED trades only).
    for sym in SYMBOLS:
        s = out["summary"][sym]
        for t in out[sym]:
            if t["status"] == "closed":
                s["closed"] += 1
                pnl = t["profit_usd"] or 0.0
                s["net_pnl"] += pnl
                if pnl >= 0:
                    s["wins"] += 1
                    s["gross_win"] += pnl
                else:
                    s["losses"] += 1
                    s["gross_loss"] += pnl
            elif t["status"] == "open":
                s["open"] += 1
            elif t["status"] == "cancelled":
                s["cancelled"] += 1
        s["win_rate"] = round(s["wins"] / s["closed"] * 100, 1) if s["closed"] else None
        s["net_pnl"] = round(s["net_pnl"], 2)
        s["gross_win"] = round(s["gross_win"], 2)
        s["gross_loss"] = round(s["gross_loss"], 2)

    a = out["summary"]["all"]
    for sym in SYMBOLS:
        s = out["summary"][sym]
        for k in ("closed", "wins", "losses", "net_pnl", "gross_win", "gross_loss",
                  "open", "cancelled"):
            a[k] += s[k]
    a["win_rate"] = round(a["wins"] / a["closed"] * 100, 1) if a["closed"] else None
    a["net_pnl"] = round(a["net_pnl"], 2)
    a["gross_win"] = round(a["gross_win"], 2)
    a["gross_loss"] = round(a["gross_loss"], 2)

    return out
