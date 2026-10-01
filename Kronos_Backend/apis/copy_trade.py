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
