"""Dedicated LOCAL paper-trading account for prediction-market bets
(Polymarket + Kalshi). Separate from the MT5 account. Fee-accurate.

Start $1,000 -> target $2,000. State persisted to journal/pm_account.json.
A "share" pays $1.00 if the outcome is correct, $0 otherwise; you buy it for
its price (0..1). Fees are charged on entry per each venue's model below.

Fee models (approximations from the 2026-06 research; tune the constants):
  * Kalshi taker:    ceil(0.07 * C * P * (1-P)) per order, in cents
                     (peak ~1.75c per contract at P=0.50).
  * Polymarket taker: ~1.8% of $1 notional peak at P=0.50, shaped by P*(1-P)
                     -> 0.072 * shares * P*(1-P) (peak ~1.8c/share at 0.50).
Makers pay ~0; we model the conservative TAKER case (you cross the spread).

CLI:  python -m bot.paper_pm           (status)
"""
import json
import math
import os
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNT_PATH = os.path.join(_ROOT, "journal", "pm_account.json")
START_BALANCE = 1000.0
TARGET = 2000.0


def _now():
    return datetime.now(timezone.utc).isoformat()


def fee(venue, shares, price):
    """Entry fee in $ for buying `shares` of an outcome at `price` on `venue`."""
    p = max(0.0, min(1.0, price))
    if str(venue).lower().startswith("k"):  # kalshi: ceil to cent per order
        return math.ceil(0.07 * shares * p * (1 - p) * 100) / 100.0
    return round(shares * 0.072 * p * (1 - p), 4)  # polymarket taker approx


def _blank():
    return {"start_balance": START_BALANCE, "balance": START_BALANCE,
            "target": TARGET, "positions": [], "history": [],
            "next_id": 1, "created_at": _now()}


def load():
    if not os.path.exists(ACCOUNT_PATH):
        return _blank()
    try:
        with open(ACCOUNT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _blank()


def save(acc):
    tmp = ACCOUNT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(acc, f, indent=2)
    os.replace(tmp, ACCOUNT_PATH)


def buy(acc, venue, market, side, shares, price, settles=None, tag="",
        purpose="", fee_override=None):
    """Buy `shares` of an outcome. Deducts cost+fee from balance. Returns pos."""
    cost = round(shares * price, 4)
    f = fee_override if fee_override is not None else fee(venue, shares, price)
    total = round(cost + f, 4)
    if total > acc["balance"] + 1e-9:
        return None
    acc["balance"] = round(acc["balance"] - total, 4)
    pos = {"id": acc["next_id"], "venue": venue, "market": market, "side": side,
           "shares": shares, "price": price, "cost": cost, "fee": f,
           "opened_at": _now(), "settles": settles, "tag": tag,
           "purpose": purpose, "status": "open"}
    acc["next_id"] += 1
    acc["positions"].append(pos)
    return pos


def buy_lock(acc, shares, lock_cost, fee_total, settles, legs, purpose,
             market="cross-venue-15m", tag="arb15m"):
    """Record a cross-venue lock as ONE position (UP one venue + DOWN other).

    Pays `shares` x $1 at settlement (one leg always wins in the single-
    reference model). Cost = shares*lock_cost + both legs' fees.
    """
    cost = round(shares * lock_cost, 4)
    total = round(cost + fee_total, 4)
    if total > acc["balance"] + 1e-9:
        return None
    acc["balance"] = round(acc["balance"] - total, 4)
    pos = {"id": acc["next_id"], "venue": "Polymarket+Kalshi", "market": market,
           "side": "LOCK", "shares": shares, "price": round(lock_cost, 4),
           "cost": cost, "fee": round(fee_total, 4), "opened_at": _now(),
           "settles": settles, "tag": tag, "purpose": purpose, "legs": legs,
           "status": "open"}
    acc["next_id"] += 1
    acc["positions"].append(pos)
    return pos


def settle(acc, pos, won=None, payout_per_unit=None):
    """Settle a position. Pass `won` (bool -> pays shares*$1 or $0) for a simple
    binary, OR `payout_per_unit` for a cross-venue LOCK that can pay 0/1/2 per pair
    depending on the two venues' REAL settlements: 0 = basis break (the venues
    resolved opposite -> BOTH legs lose the stake), 1 = normal (they agree, one leg
    pays), 2 = windfall (they disagree the other way, both legs win). Realizes P&L."""
    if payout_per_unit is None:
        payout_per_unit = 1.0 if won else 0.0
    payout = round(pos["shares"] * payout_per_unit, 4)
    acc["balance"] = round(acc["balance"] + payout, 4)
    pos["status"] = "settled"
    pos["payout"] = payout
    pos["payout_per_unit"] = round(payout_per_unit, 4)
    pos["won"] = bool(payout_per_unit >= 1.0) if won is None else won
    pos["pnl"] = round(payout - pos["cost"] - pos["fee"], 4)
    pos["closed_at"] = _now()
    acc["positions"] = [p for p in acc["positions"] if p["id"] != pos["id"]]
    acc["history"].append(pos)
    return pos


def account(acc, mark=None):
    """Summary incl. equity (open positions marked at `mark` price map)."""
    open_val = 0.0
    for p in acc["positions"]:
        mp = (mark or {}).get(p.get("market"))
        open_val += p["shares"] * (mp if mp is not None else p["price"])
    equity = round(acc["balance"] + open_val, 2)
    realized = round(sum(h.get("pnl", 0) for h in acc["history"]), 2)
    wins = sum(1 for h in acc["history"] if h.get("won"))
    n = len(acc["history"])
    start, tgt = acc["start_balance"], acc["target"]
    prog = max(0.0, min(100.0, (equity - start) / (tgt - start) * 100))
    return {"balance": round(acc["balance"], 2), "equity": equity,
            "open_value": round(open_val, 2), "realized_pnl": realized,
            "start": start, "target": tgt, "progress_pct": round(prog, 1),
            "open_positions": len(acc["positions"]), "settled_trades": n,
            "win_rate": round(wins / n * 100, 1) if n else None,
            "total_fees": round(sum(h.get("fee", 0) for h in acc["history"])
                                + sum(p.get("fee", 0) for p in acc["positions"]), 2)}


def reset():
    save(_blank())


if __name__ == "__main__":
    print(json.dumps(account(load()), indent=2))
