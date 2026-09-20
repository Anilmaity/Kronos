"""MT5-terminal candle source for symbols OANDA lacks (e.g. BTCUSDT).

Same output shape as bot.data.candles(). MT5 returns server time (UTC+3 for
Winprofx); times here are corrected to real UTC ISO strings.
"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

SERVER_UTC_OFFSET_HOURS = 3

_TF = {
    "M1": mt5.TIMEFRAME_M1, "M3": mt5.TIMEFRAME_M3,
    "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D": mt5.TIMEFRAME_D1,
    "W": mt5.TIMEFRAME_W1,
}

_initialized = False


def _ensure():
    global _initialized
    if not _initialized:
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        _initialized = True


def candles(symbol: str, granularity: str = "H1", count: int = 200) -> list:
    _ensure()
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, _TF[granularity], 0, count)
    if rates is None:
        raise RuntimeError(f"no rates for {symbol} {granularity}: {mt5.last_error()}")
    out = []
    offset = timedelta(hours=SERVER_UTC_OFFSET_HOURS)
    for i, r in enumerate(rates):
        utc = datetime.fromtimestamp(int(r["time"]), timezone.utc) - offset
        out.append({
            "time": utc.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
            "o": float(r["open"]), "h": float(r["high"]),
            "l": float(r["low"]), "c": float(r["close"]),
            "volume": int(r["tick_volume"]),
            # last bar in copy_rates_from_pos is the forming one
            "complete": i < len(rates) - 1,
        })
    return out


def current_price(symbol: str) -> dict:
    _ensure()
    mt5.symbol_select(symbol, True)
    t = mt5.symbol_info_tick(symbol)
    if t is None or not t.bid:
        raise RuntimeError(f"no tick for {symbol}")
    utc = datetime.fromtimestamp(t.time, timezone.utc) - timedelta(
        hours=SERVER_UTC_OFFSET_HOURS)
    return {"bid": t.bid, "ask": t.ask, "mid": round((t.bid + t.ask) / 2, 2),
            "time": utc.isoformat()}
