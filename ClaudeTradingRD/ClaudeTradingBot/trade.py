"""Validated trade execution (multi-symbol: XAUUSD, BTCUSDT, ...).

Usage:
  python trade.py buy|sell SL TP [lots] [symbol]   # market order, absolute SL/TP
  python trade.py close <positionId>
  python trade.py modify <positionId> SL TP
  python trade.py cancel <orderId>

Risk is computed from the symbol's real contract size. One position per
symbol max. Every event is appended to journal/orders.csv and journal.md.
"""
import sys, json
from datetime import datetime, timezone
from bot import broker, orders_log

MAX_RISK_USD = 28.0      # 3% hard cap
WARN_RISK_USD = 19.0     # 2% soft cap
DEFAULT_SYMBOL = "XAUUSD"


def _journal(line: str):
    with open("journal/journal.md", "a", encoding="utf-8") as f:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        f.write(f"\n- {now} UTC — {line}\n")


def main():
    args = sys.argv[1:]
    cmd = args[0]

    if cmd == "close":
        pos = [p for p in broker.positions() if p["id"] == args[1]]
        result = broker.close_position(args[1])
        print(json.dumps(result, default=str))
        p = pos[0] if pos else {}
        bal = broker.account_information()["balance"]
        orders_log.append("close", symbol=p.get("symbol", "?"),
                          side=p.get("type", ""), lots=p.get("volume", ""),
                          price=p.get("currentPrice", ""),
                          position_id=args[1], profit_usd=p.get("profit", ""),
                          balance_after=bal, order_id=result.get("orderId", ""))
        _journal(f"CLOSE position {args[1]} ({p.get('symbol', '?')}) "
                 f"P&L ~${p.get('profit', '?')}, balance {bal}")
        return
    if cmd == "cancel":
        result = broker.cancel_order(args[1])
        print(json.dumps(result, default=str))
        orders_log.append("cancel", order_id=args[1])
        _journal(f"CANCEL order {args[1]}")
        return
    if cmd == "modify":
        result = broker.modify_position(args[1], float(args[2]), float(args[3]))
        print(json.dumps(result, default=str))
        orders_log.append("modify", position_id=args[1], sl=args[2], tp=args[3])
        _journal(f"MODIFY position {args[1]} SL {args[2]} TP {args[3]}")
        return

    assert cmd in ("buy", "sell"), f"unknown command {cmd}"
    sl, tp = float(args[1]), float(args[2])
    lots = float(args[3]) if len(args) > 3 else 0.01
    symbol = args[4] if len(args) > 4 else DEFAULT_SYMBOL

    spec = broker.symbol_spec(symbol)
    contract = spec["contractSize"]
    p = broker.symbol_price(symbol)
    ref = p["ask"] if cmd == "buy" else p["bid"]
    if cmd == "buy":
        assert sl < ref < tp, f"buy needs SL<{ref}<TP, got SL={sl} TP={tp}"
    else:
        assert tp < ref < sl, f"sell needs TP<{ref}<SL, got SL={sl} TP={tp}"

    risk = abs(ref - sl) * lots * contract
    reward = abs(tp - ref) * lots * contract
    rr = reward / risk if risk else 0
    print(f"{symbol} price={ref} contract={contract} "
          f"risk=${risk:.2f} reward=${reward:.2f} RR={rr:.2f}")
    assert risk <= MAX_RISK_USD, f"risk ${risk:.2f} exceeds hard cap ${MAX_RISK_USD}"
    if risk > WARN_RISK_USD:
        print(f"WARN: risk above ${WARN_RISK_USD} soft cap")
    assert rr >= 1.8, f"RR {rr:.2f} below 1.8 minimum"

    existing = [q for q in broker.positions() if q["symbol"] == symbol]
    assert not existing, f"already in a {symbol} position: {existing}"

    result = broker.market_order(cmd, lots, sl, tp, symbol=symbol)
    print("RESULT:", json.dumps(result, default=str))

    orders_log.append("open", symbol=symbol, side=cmd, lots=lots, price=ref,
                      sl=sl, tp=tp, risk_usd=round(risk, 2), rr=round(rr, 2),
                      order_id=result.get("orderId", ""),
                      position_id=result.get("positionId", ""))
    _journal(f"OPEN {cmd.upper()} {lots} {symbol} @ ~{ref}, SL {sl}, TP {tp}, "
             f"risk ${risk:.2f}, RR {rr:.1f} — order {result.get('orderId', '?')}")


if __name__ == "__main__":
    main()
