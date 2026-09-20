"""Broker-agnostic execution interface.

Every adapter returns MetaApi-style camelCase dict shapes so the consumers
(trade.py, status.py, check.py, dashboard) never care which backend is active.
Money values are floats in account currency; prices are absolute; volume is lots.
"""
from abc import ABC, abstractmethod


class Broker(ABC):
    name: str = "?"
    symbol: str = "XAUUSD"

    @abstractmethod
    def account_information(self) -> dict:
        """{platform, broker, currency, server, balance, equity, margin,
        freeMargin, leverage, login, name, tradeAllowed}"""

    @abstractmethod
    def positions(self) -> list:
        """[{id, symbol, type: POSITION_TYPE_BUY|SELL, volume, openPrice,
        currentPrice, stopLoss, takeProfit, profit, swap, time, comment, magic}]"""

    @abstractmethod
    def pending_orders(self) -> list:
        """[{id, symbol, type: ORDER_TYPE_*, volume, openPrice, stopLoss,
        takeProfit, time, comment}]"""

    @abstractmethod
    def symbol_spec(self, symbol: str = None) -> dict:
        """{symbol, description, digits, point, contractSize, minVolume,
        maxVolume, volumeStep, spread}"""

    @abstractmethod
    def symbol_price(self, symbol: str = None) -> dict:
        """{symbol, bid, ask, time}"""

    @abstractmethod
    def deals_history(self, start: str, end: str) -> list:
        """ISO timestamps. Closed deals in window."""

    @abstractmethod
    def market_order(self, side: str, volume: float, stop_loss: float,
                     take_profit: float, symbol: str = None,
                     comment: str = "claude-bot") -> dict:
        """side: 'buy'|'sell'. SL/TP absolute prices, mandatory.
        Returns {orderId, positionId, numericCode, stringCode}."""

    @abstractmethod
    def limit_order(self, side: str, volume: float, price: float,
                    stop_loss: float, take_profit: float, symbol: str = None,
                    comment: str = "claude-bot") -> dict:
        pass

    @abstractmethod
    def modify_position(self, position_id: str, stop_loss: float = None,
                        take_profit: float = None) -> dict:
        pass

    @abstractmethod
    def close_position(self, position_id: str) -> dict:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> dict:
        pass
