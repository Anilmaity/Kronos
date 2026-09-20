"""Prediction-market PAPER account CLI (Polymarket + Kalshi, fee-accurate).

Separate from the MT5 account. Start $1,000 -> target $2,000.

Usage:
  python pmpaper.py                 # status + open positions + order history
  python pmpaper.py reset           # wipe back to the $1,000 start
"""
import sys
from bot import paper_pm


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        paper_pm.reset()
        print("PM paper account reset to $%.0f" % paper_pm.START_BALANCE)
        return

    acc = paper_pm.load()
    a = paper_pm.account(acc)
    bar = int(a["progress_pct"] / 5)
    print("=== PM PAPER ACCOUNT (Polymarket + Kalshi) ===")
    print(f"  Balance ${a['balance']:.2f} | Equity ${a['equity']:.2f} | "
          f"Realized ${a['realized_pnl']:+.2f} | Fees ${a['total_fees']:.2f}")
    print(f"  ${a['start']:.0f} ->  [{'#'*bar}{'.'*(20-bar)}]  ${a['target']:.0f}  "
          f"({a['progress_pct']:.1f}%)")
    print(f"  Trades: {a['settled_trades']} settled"
          + (f", win rate {a['win_rate']:.0f}%" if a['win_rate'] is not None else "")
          + f", {a['open_positions']} open")

    if acc["positions"]:
        print("\n  OPEN:")
        for p in acc["positions"]:
            print(f"   #{p['id']} {p['side']} x{p['shares']} @ {p['price']*100:.0f}c "
                  f"cost ${p['cost']:.2f} fee ${p['fee']:.2f} settles {p.get('settles')}")
            if p.get("purpose"):
                print(f"        purpose: {p['purpose']}")

    if acc["history"]:
        print("\n  ORDER HISTORY (most recent):")
        for h in reversed(acc["history"][-12:]):
            res = "WON " if h.get("won") else "LOST"
            print(f"   #{h['id']} {h['side']} x{h['shares']} @ {h['price']*100:.0f}c | "
                  f"{res} | P&L ${h.get('pnl', 0):+.2f} | fee ${h['fee']:.2f}")
            if h.get("purpose"):
                print(f"        {h['purpose']}")


if __name__ == "__main__":
    main()
