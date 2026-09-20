"""MetaApi cloud REST adapter (london region) — works on any OS, no terminal.

Kept as the fallback/AWS-Linux backend. Select with BROKER=metaapi.
"""
import os
import time

import requests

from .base import Broker

BASE = "https://mt-client-api-v1.london.agiliumtrade.ai"


class MetaApiBroker(Broker):
    name = "metaapi"

    def __init__(self):
        self.account_id = os.getenv("META_ACCOUNT_ID")
        self.headers = {"auth-token": os.getenv("META_API_TOKEN"),
                        "Content-Type": "application/json"}

    def _url(self, path: str) -> str:
        return f"{BASE}/users/current/accounts/{self.account_id}/{path}"

    def _get(self, path: str, retries: int = 3):
        last = None
        for _ in range(retries):
            try:
                r = requests.get(self._url(path), headers=self.headers, timeout=30)
                if r.status_code in (502, 504):
                    last = r.text
                    time.sleep(3)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                last = str(e)
                time.sleep(3)
        raise RuntimeError(f"GET {path} failed: {last}")

    def _trade(self, payload: dict) -> dict:
        r = requests.post(self._url("trade"), headers=self.headers,
                          json=payload, timeout=60)
        try:
            body = r.json()
        except ValueError:
            body = {"raw": r.text}
        if not r.ok:
            raise RuntimeError(f"trade failed [{r.status_code}]: {body}")
        return body

    def account_information(self) -> dict:
        return self._get("account-information")

    def positions(self) -> list:
        return self._get("positions")

    def pending_orders(self) -> list:
        return self._get("orders")

    def symbol_spec(self, symbol: str = None) -> dict:
        return self._get(f"symbols/{symbol or self.symbol}/specification")

    def symbol_price(self, symbol: str = None) -> dict:
        return self._get(f"symbols/{symbol or self.symbol}/current-price")

    def deals_history(self, start: str, end: str) -> list:
        return self._get(f"history-deals/time/{start}/{end}")

    def market_order(self, side, volume, stop_loss, take_profit,
                     symbol=None, comment="claude-bot") -> dict:
        assert side in ("buy", "sell")
        assert stop_loss and take_profit, "SL and TP are required on every trade"
        return self._trade({
            "actionType": "ORDER_TYPE_BUY" if side == "buy" else "ORDER_TYPE_SELL",
            "symbol": symbol or self.symbol,
            "volume": round(volume, 2),
            "stopLoss": round(stop_loss, 2),
            "takeProfit": round(take_profit, 2),
            "comment": comment,
        })

    def limit_order(self, side, volume, price, stop_loss, take_profit,
                    symbol=None, comment="claude-bot") -> dict:
        assert side in ("buy", "sell")
        return self._trade({
            "actionType": "ORDER_TYPE_BUY_LIMIT" if side == "buy" else "ORDER_TYPE_SELL_LIMIT",
            "symbol": symbol or self.symbol,
            "volume": round(volume, 2),
            "openPrice": round(price, 2),
            "stopLoss": round(stop_loss, 2),
            "takeProfit": round(take_profit, 2),
            "comment": comment,
        })

    def modify_position(self, position_id, stop_loss=None, take_profit=None) -> dict:
        payload = {"actionType": "POSITION_MODIFY", "positionId": str(position_id)}
        if stop_loss is not None:
            payload["stopLoss"] = round(stop_loss, 2)
        if take_profit is not None:
            payload["takeProfit"] = round(take_profit, 2)
        return self._trade(payload)

    def close_position(self, position_id) -> dict:
        return self._trade({"actionType": "POSITION_CLOSE_ID",
                            "positionId": str(position_id)})

    def cancel_order(self, order_id) -> dict:
        return self._trade({"actionType": "ORDER_CANCEL", "orderId": str(order_id)})
