"""Telegram copy-trade sources shown as their own dashboard tabs.

The Neymar / Neymar VIP copy-traders (KronosStrategies/Telegram_Bot) trade every
account that has a UserStrategy on their Strategy, at that row's fixed
`lot_size`. Keep these ids in sync with the frontend's strategySources.ts.
"""
from decimal import Decimal, InvalidOperation

# source -> Strategy ids shown on that tab. The first id is the one new accounts
# are added under (the strategy the copy-trader loads extra accounts from).
SOURCE_STRATEGY_IDS = {
    "neymar": [
        "d9bf1604-9ee0-4454-b3c1-b7335ff8915f",  # Neymar Telegram Copy
        "30427449-9705-406c-820d-2b5ff9d8c003",  # Neymar Telegram Copy (Account 2)
    ],
    "neymar-vip": [
        "c708a216-5c5f-41b4-a63b-7e13d15ce090",  # Neymar VIP
    ],
}

# XAUUSD lot rules at the broker: 0.01 minimum, 0.01 step.
LOT_STEP = Decimal("0.01")
LOT_MIN = Decimal("0.01")
LOT_MAX = Decimal("100")


def parse_lot(value) -> tuple[Decimal | None, str | None]:
    """Validate a lot size. Returns (lot, None) or (None, error message)."""
    try:
        lot = Decimal(str(value)).normalize()
    except (InvalidOperation, ValueError, TypeError):
        return None, "Price must be a number, e.g. 0.1"
    if not lot.is_finite():
        return None, "Price must be a number, e.g. 0.1"
    if lot < LOT_MIN:
        return None, "Price must be at least 0.01"
    if lot > LOT_MAX:
        return None, "Price must be at most 100"
    if lot % LOT_STEP != 0:
        return None, "Price must be in steps of 0.01 (e.g. 0.1, 0.25)"
    return lot.quantize(LOT_STEP), None


# ── Stop loss / drawdown settings ─────────────────────────────────────────────
DEFAULT_MAX_SL_PER_TRADE = Decimal("90")
DEFAULT_DAILY_DD_OFFSET = Decimal("230")
DEFAULT_MAX_DD_OFFSET = Decimal("500")
# Equity within this many USD above a floor = no new trades for the day; the
# copy-trader uses the same buffer.
DD_BUFFER = Decimal("10")
MONEY_MAX = Decimal("1000000000")


def parse_money(value, label: str) -> tuple[Decimal | None, str | None]:
    """Optional positive USD amount. None/'' -> (None, None) = not set."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, None
    try:
        v = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None, f"{label} must be a number"
    if not v.is_finite() or v <= 0:
        return None, f"{label} must be greater than 0"
    if v > MONEY_MAX:
        return None, f"{label} is too large"
    return v.quantize(Decimal("0.01")), None


def parse_risk(*, trade_sl_usd=None, max_sl_per_trade_usd=None, daily_dd_floor=None,
               max_dd_floor=None, daily_dd_offset=None, max_dd_offset=None,
               last_equity=None) -> tuple[dict | None, str | None]:
    """Validate the stop-loss / drawdown fields of the Add Data / settings popups.

    Daily / Max drawdown are LOSS AMOUNTS in USD (`daily_dd_offset` /
    `max_dd_offset`): the equity floors are derived — now from the account's
    current equity, and every new broker day from that day's starting equity
    (floor = equity - amount). `daily_dd_floor` / `max_dd_floor` arguments are
    accepted for old clients but ignored; the floors are computed here / by the
    copy-trader. Returns ({field: Decimal | None}, None) or (None, error).
    Max SL per trade defaults to 90 when a Trade SL is set (empty otherwise =
    the copy-trader's $90).
    """
    out = {}
    for key, raw, label in (
        ("trade_sl_usd", trade_sl_usd, "Trade SL"),
        ("max_sl_per_trade_usd", max_sl_per_trade_usd, "Max SL per trade"),
        ("daily_dd_offset", daily_dd_offset, "Daily drawdown"),
        ("max_dd_offset", max_dd_offset, "Max drawdown"),
    ):
        v, err = parse_money(raw, label)
        if err:
            return None, err
        out[key] = v

    if out["trade_sl_usd"] is not None and out["max_sl_per_trade_usd"] is None:
        out["max_sl_per_trade_usd"] = DEFAULT_MAX_SL_PER_TRADE

    eq = Decimal(str(last_equity)) if last_equity is not None else None
    for amount_key, floor_key, label in (("daily_dd_offset", "daily_dd_floor", "Daily drawdown"),
                                         ("max_dd_offset", "max_dd_floor", "Max drawdown")):
        amount = out[amount_key]
        if amount is not None and eq is not None and amount >= eq - DD_BUFFER:
            return None, (f"{label} {amount} is not smaller than the account's equity "
                          f"{eq.quantize(Decimal('0.01'))} — it would stop the account at once")
        # Floor from the current equity when known; otherwise the copy-trader
        # sets it from the first equity it reads.
        out[floor_key] = (eq - amount).quantize(Decimal("0.01")) if amount is not None and eq is not None else None
    return out, None


def apply_drawdown(broker, risk: dict) -> list[str]:
    """Copy the drawdown amounts (+ derived floors) onto a UserBroker. dd_day is
    cleared so the copy-trader adopts these floors for the current broker day
    and resets them from equity at the next one; a day already blocked stays
    blocked."""
    fields = ["daily_dd_floor", "max_dd_floor", "daily_dd_offset", "max_dd_offset"]
    changed = any(getattr(broker, f) != risk[f] for f in fields)
    for f in fields:
        setattr(broker, f, risk[f])
    if changed:
        broker.dd_day = None
        if risk["daily_dd_offset"] is None and risk["max_dd_offset"] is None:
            broker.dd_status = ""
        return fields + ["dd_day", "dd_status"]
    return []


# Telegram channel each copy-trade tab trades (tg_signals.channel).
SOURCE_CHANNEL = {
    "neymar": "NeymarGoldTrader",
    "neymar-vip": "-1002776523643",
}
