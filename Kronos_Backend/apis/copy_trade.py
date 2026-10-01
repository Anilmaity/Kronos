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
DEFAULT_MAX_DD_OFFSET = Decimal("470")
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

    Returns ({field: Decimal | None}, None) or (None, error). Defaults: max SL per
    trade 90 when a Trade SL is set (empty otherwise = the copy-trader's $90); day-reset offsets 230 / 470 when a floor is set.
    A floor at or above the last known equity (minus the buffer) is refused — it
    would close every trade / block the account the moment it is saved.
    """
    out = {}
    for key, raw, label in (
        ("trade_sl_usd", trade_sl_usd, "Trade SL"),
        ("max_sl_per_trade_usd", max_sl_per_trade_usd, "Max SL per trade"),
        ("daily_dd_floor", daily_dd_floor, "Daily drawdown"),
        ("max_dd_floor", max_dd_floor, "Max drawdown"),
        ("daily_dd_offset", daily_dd_offset, "Daily reset amount"),
        ("max_dd_offset", max_dd_offset, "Max reset amount"),
    ):
        v, err = parse_money(raw, label)
        if err:
            return None, err
        out[key] = v

    # Max SL per trade also caps the channel's own SL (empty = the bot's $90).
    if out["trade_sl_usd"] is not None and out["max_sl_per_trade_usd"] is None:
        out["max_sl_per_trade_usd"] = DEFAULT_MAX_SL_PER_TRADE

    if out["daily_dd_floor"] is None:
        out["daily_dd_offset"] = None
    elif out["daily_dd_offset"] is None:
        out["daily_dd_offset"] = DEFAULT_DAILY_DD_OFFSET
    if out["max_dd_floor"] is None:
        out["max_dd_offset"] = None
    elif out["max_dd_offset"] is None:
        out["max_dd_offset"] = DEFAULT_MAX_DD_OFFSET

    if last_equity is not None:
        eq = Decimal(str(last_equity))
        for key, label in (("daily_dd_floor", "Daily drawdown"), ("max_dd_floor", "Max drawdown")):
            floor = out[key]
            if floor is not None and floor >= eq - DD_BUFFER:
                return None, (f"{label} {floor} is not below the account's current equity "
                              f"{eq.quantize(Decimal('0.01'))} (minus {DD_BUFFER}) — it would stop "
                              f"the account immediately")
    return out, None


def apply_drawdown(broker, risk: dict) -> list[str]:
    """Copy the drawdown fields onto a UserBroker. The copy-trader adopts new
    floors for the current broker day (dd_day cleared) — it never resets them
    until the next day; a day already blocked stays blocked."""
    fields = ["daily_dd_floor", "max_dd_floor", "daily_dd_offset", "max_dd_offset"]
    changed = any(getattr(broker, f) != risk[f] for f in fields)
    for f in fields:
        setattr(broker, f, risk[f])
    if changed:
        broker.dd_day = None
        if risk["daily_dd_floor"] is None and risk["max_dd_floor"] is None:
            broker.dd_status = ""
        return fields + ["dd_day", "dd_status"]
    return []
