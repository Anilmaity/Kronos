"""ONE-SHOT live connectivity test for the Polymarket V2 order path.

Places a single NON-FILLABLE limit order (a low bid that just rests in the book
and will not match), prints the CLOB response, then immediately CANCELS it.

Purpose: prove the CLOB V2 accepts an order from this proxy wallet (auth +
balance validation) despite get_balance_allowance reading 0. Near-zero money at
risk — the bid is far below market and is cancelled right away.

Run it yourself (real money mode):
    set DRY_RUN=false   (PowerShell:  $env:DRY_RUN="false")
    .venv\\Scripts\\python.exe poly_test_order.py

Optional args:  poly_test_order.py [price] [size]   (default 0.05  20)
"""
import os
import sys

os.environ.setdefault("DRY_RUN", "false")  # this script is explicitly a live test

from bot import secrets, polymarket, exec_polymarket as P  # noqa: E402

PRICE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05
SIZE = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0


def main():
    print(f"DRY_RUN={P.dry_run()}  funder={os.getenv('POLY_FUNDER')}")
    print("pUSD balance:", P.balance_detail())
    print("allowances  :", P.allowance_status()["ready"])

    # Pick the current 15m window's cheaper side to bid on (won't fill).
    w = polymarket.updown_window_live("15m", 900) or polymarket.updown_window_live("5m", 300)
    if not w:
        print("no live window — aborting")
        return
    token = w.get("down_token") or w.get("up_token")
    print(f"market: {w.get('slug')}  token: {str(token)[:20]}…  "
          f"down_cost={w.get('down_cost')}  bidding {PRICE} x {SIZE} (= ${PRICE*SIZE:.2f})")
    if not token:
        print("no token id — aborting")
        return

    resp = P.place_limit_gtc(token, PRICE, SIZE, side="BUY")
    print("\nORDER RESPONSE:", resp)
    oid = resp.get("orderID") or resp.get("orderId") or resp.get("id")
    if oid:
        print(">>> ACCEPTED — the live order path WORKS. order_id:", oid)
        print("cancel:", P.cancel(oid))
    else:
        print(">>> NOT accepted — inspect the response/error above "
              "(if it says balance/allowance, the EOA-binding bug blocks us).")


if __name__ == "__main__":
    main()
