"""Backward-compat shim — implementations live in bot/brokers/.

The active backend is chosen by the BROKER env var (see bot/brokers/__init__.py):
mt5 = native terminal (default), metaapi = cloud REST fallback.
Existing callers (trade.py, status.py, check.py, dashboard) keep working unchanged.
"""
from bot.brokers import get_broker

SYMBOL = "XAUUSD"


def account_information() -> dict:
    return get_broker().account_information()


def positions() -> list:
    return get_broker().positions()


def pending_orders() -> list:
    return get_broker().pending_orders()


def symbol_spec(symbol: str = SYMBOL) -> dict:
    return get_broker().symbol_spec(symbol)


def symbol_price(symbol: str = SYMBOL) -> dict:
    return get_broker().symbol_price(symbol)


def deals_history(start: str, end: str) -> list:
    return get_broker().deals_history(start, end)


def market_order(side: str, volume: float, stop_loss: float, take_profit: float,
                 symbol: str = SYMBOL, comment: str = "claude-bot") -> dict:
    return get_broker().market_order(side, volume, stop_loss, take_profit,
                                     symbol, comment)


def limit_order(side: str, volume: float, price: float, stop_loss: float,
                take_profit: float, symbol: str = SYMBOL,
                comment: str = "claude-bot") -> dict:
    return get_broker().limit_order(side, volume, price, stop_loss, take_profit,
                                    symbol, comment)


def modify_position(position_id: str, stop_loss: float = None,
                    take_profit: float = None) -> dict:
    return get_broker().modify_position(position_id, stop_loss, take_profit)


def close_position(position_id: str) -> dict:
    return get_broker().close_position(position_id)


def cancel_order(order_id: str) -> dict:
    return get_broker().cancel_order(order_id)
