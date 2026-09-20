"""Native MetaTrader5 adapter — talks to the local MT5 terminal over IPC.

Windows-only (locally now, Windows EC2 on AWS later). The terminal must either
already be logged into the account with the password saved, or
MT5_LOGIN / MT5_PASSWORD / MT5_SERVER must be set in .env.
Select with BROKER=mt5.
"""
import os
from datetime import datetime, timezone

from .base import Broker

_TERMINAL_DEFAULT = r"C:\Program Files\MetaTrader 5\terminal64.exe"

_ORDER_TYPES = {
    0: "ORDER_TYPE_BUY", 1: "ORDER_TYPE_SELL",
    2: "ORDER_TYPE_BUY_LIMIT", 3: "ORDER_TYPE_SELL_LIMIT",
    4: "ORDER_TYPE_BUY_STOP", 5: "ORDER_TYPE_SELL_STOP",
    6: "ORDER_TYPE_BUY_STOP_LIMIT", 7: "ORDER_TYPE_SELL_STOP_LIMIT",
}
_DEAL_TYPES = {0: "DEAL_TYPE_BUY", 1: "DEAL_TYPE_SELL", 2: "DEAL_TYPE_BALANCE"}


def _iso(epoch_seconds) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


class Mt5NativeBroker(Broker):
    name = "mt5_native"

    def __init__(self):
        import MetaTrader5 as mt5
        self.mt5 = mt5
        self._connected = False

    def _ensure(self):
        if self._connected:
            return
        mt5 = self.mt5
        path = os.getenv("MT5_TERMINAL_PATH", _TERMINAL_DEFAULT)
        login = os.getenv("MT5_LOGIN")

        # Attach-first: initialize with credentials is flaky (IPC timeout even
        # when the terminal-side login succeeds), so attach plain and only push
        # a login if the terminal is on the wrong account.
        attached = mt5.initialize(path=path)
        if attached and login and (mt5.account_info() is None
                                   or mt5.account_info().login != int(login)):
            if not mt5.login(int(login), password=os.environ["MT5_PASSWORD"],
                             server=os.getenv("MT5_SERVER", "Winprofx-Live")):
                code, msg = mt5.last_error()
                mt5.shutdown()
                raise RuntimeError(f"MT5 login({login}) failed [{code}] {msg}")
        elif not attached and login:
            attached = mt5.initialize(
                path=path, login=int(login),
                password=os.environ["MT5_PASSWORD"],
                server=os.getenv("MT5_SERVER", "Winprofx-Live"),
                timeout=120_000)

        if not attached:
            code, msg = mt5.last_error()
            raise RuntimeError(
                f"MT5 initialize failed [{code}] {msg}. Either open the terminal "
                "and log into the Winprofx demo once (tick 'Save password'), or "
                "set MT5_LOGIN / MT5_PASSWORD / MT5_SERVER in .env. "
                "Fallback: set BROKER=metaapi.")
        ai = mt5.account_info()
        if ai is None:
            mt5.shutdown()
            raise RuntimeError("MT5 terminal running but no account logged in")
        if login and ai.login != int(login):
            mt5.shutdown()
            raise RuntimeError(
                f"MT5 terminal is on account {ai.login}, expected {login}")
        mt5.symbol_select(self.symbol, True)
        self._connected = True

    def _filling(self, symbol: str):
        mt5 = self.mt5
        si = mt5.symbol_info(symbol)
        fm = si.filling_mode if si else 0
        if fm & 2:
            return mt5.ORDER_FILLING_IOC
        if fm & 1:
            return mt5.ORDER_FILLING_FOK
        return mt5.ORDER_FILLING_RETURN

    def _send(self, req: dict) -> dict:
        mt5 = self.mt5
        res = mt5.order_send(req)
        if res is None:
            raise RuntimeError(f"order_send returned None: {mt5.last_error()} req={req}")
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"trade failed [{res.retcode}]: {res.comment} req={req}")
        return {
            "numericCode": res.retcode,
            "stringCode": res.comment,
            "orderId": str(res.order) if res.order else None,
            "dealId": str(res.deal) if res.deal else None,
            # opening order ticket == position ticket on MT5
            "positionId": str(res.order) if res.order else None,
        }

    def account_information(self) -> dict:
        self._ensure()
        ai = self.mt5.account_info()
        return {
            "platform": "mt5", "broker": ai.company, "currency": ai.currency,
            "server": ai.server, "balance": ai.balance, "equity": ai.equity,
            "margin": ai.margin, "freeMargin": ai.margin_free,
            "leverage": ai.leverage, "login": ai.login, "name": ai.name,
            "tradeAllowed": bool(ai.trade_allowed),
        }

    def positions(self) -> list:
        self._ensure()
        mt5 = self.mt5
        out = []
        for p in (mt5.positions_get() or []):
            out.append({
                "id": str(p.ticket), "symbol": p.symbol,
                "type": "POSITION_TYPE_BUY" if p.type == mt5.POSITION_TYPE_BUY
                        else "POSITION_TYPE_SELL",
                "volume": p.volume, "openPrice": p.price_open,
                "currentPrice": p.price_current, "stopLoss": p.sl,
                "takeProfit": p.tp, "profit": p.profit, "swap": p.swap,
                "time": _iso(p.time), "comment": p.comment, "magic": p.magic,
            })
        return out

    def pending_orders(self) -> list:
        self._ensure()
        out = []
        for o in (self.mt5.orders_get() or []):
            out.append({
                "id": str(o.ticket), "symbol": o.symbol,
                "type": _ORDER_TYPES.get(o.type, str(o.type)),
                "volume": o.volume_current, "openPrice": o.price_open,
                "stopLoss": o.sl, "takeProfit": o.tp,
                "time": _iso(o.time_setup), "comment": o.comment,
            })
        return out

    def symbol_spec(self, symbol: str = None) -> dict:
        self._ensure()
        symbol = symbol or self.symbol
        si = self.mt5.symbol_info(symbol)
        if si is None:
            raise RuntimeError(f"unknown symbol {symbol}")
        return {
            "symbol": symbol, "description": si.description,
            "digits": si.digits, "point": si.point,
            "contractSize": si.trade_contract_size,
            "minVolume": si.volume_min, "maxVolume": si.volume_max,
            "volumeStep": si.volume_step, "spread": si.spread,
        }

    def symbol_price(self, symbol: str = None) -> dict:
        self._ensure()
        symbol = symbol or self.symbol
        t = self.mt5.symbol_info_tick(symbol)
        if t is None:
            raise RuntimeError(f"no tick for {symbol}")
        return {"symbol": symbol, "bid": t.bid, "ask": t.ask, "time": _iso(t.time)}

    def deals_history(self, start: str, end: str) -> list:
        self._ensure()
        dt_start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        dt_end = datetime.fromisoformat(end.replace("Z", "+00:00"))
        out = []
        for d in (self.mt5.history_deals_get(dt_start, dt_end) or []):
            out.append({
                "id": str(d.ticket), "orderId": str(d.order),
                "positionId": str(d.position_id), "symbol": d.symbol,
                "type": _DEAL_TYPES.get(d.type, str(d.type)),
                "volume": d.volume, "price": d.price, "profit": d.profit,
                "commission": d.commission, "swap": d.swap,
                "time": _iso(d.time), "comment": d.comment, "magic": d.magic,
            })
        return out

    def market_order(self, side, volume, stop_loss, take_profit,
                     symbol=None, comment="claude-bot") -> dict:
        assert side in ("buy", "sell")
        assert stop_loss and take_profit, "SL and TP are required on every trade"
        self._ensure()
        mt5 = self.mt5
        symbol = symbol or self.symbol
        tick = mt5.symbol_info_tick(symbol)
        return self._send({
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": round(volume, 2),
            "type": mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL,
            "price": tick.ask if side == "buy" else tick.bid,
            "sl": round(stop_loss, 2),
            "tp": round(take_profit, 2),
            "deviation": 20,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(symbol),
        })

    def limit_order(self, side, volume, price, stop_loss, take_profit,
                    symbol=None, comment="claude-bot") -> dict:
        assert side in ("buy", "sell")
        self._ensure()
        mt5 = self.mt5
        symbol = symbol or self.symbol
        return self._send({
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": round(volume, 2),
            "type": mt5.ORDER_TYPE_BUY_LIMIT if side == "buy"
                    else mt5.ORDER_TYPE_SELL_LIMIT,
            "price": round(price, 2),
            "sl": round(stop_loss, 2),
            "tp": round(take_profit, 2),
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(symbol),
        })

    def modify_position(self, position_id, stop_loss=None, take_profit=None) -> dict:
        self._ensure()
        mt5 = self.mt5
        pos = mt5.positions_get(ticket=int(position_id))
        if not pos:
            raise RuntimeError(f"position {position_id} not found")
        p = pos[0]
        return self._send({
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": p.symbol,
            "position": p.ticket,
            "sl": round(stop_loss, 2) if stop_loss is not None else p.sl,
            "tp": round(take_profit, 2) if take_profit is not None else p.tp,
        })

    def close_position(self, position_id) -> dict:
        self._ensure()
        mt5 = self.mt5
        pos = mt5.positions_get(ticket=int(position_id))
        if not pos:
            raise RuntimeError(f"position {position_id} not found")
        p = pos[0]
        tick = mt5.symbol_info_tick(p.symbol)
        is_buy = p.type == mt5.POSITION_TYPE_BUY
        return self._send({
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": p.symbol,
            "volume": p.volume,
            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
            "position": p.ticket,
            "price": tick.bid if is_buy else tick.ask,
            "deviation": 20,
            "comment": "claude-bot close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(p.symbol),
        })

    def cancel_order(self, order_id) -> dict:
        self._ensure()
        return self._send({
            "action": self.mt5.TRADE_ACTION_REMOVE,
            "order": int(order_id),
        })
