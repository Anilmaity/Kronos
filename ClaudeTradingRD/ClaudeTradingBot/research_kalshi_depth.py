"""READ-ONLY research: how much resting order-book depth do Kalshi's BTC markets
actually have, by horizon? Discovers every open BTC series, samples near-the-money
markets, and reports raw book depth (yes/no bid levels + total contracts) + last
trade. No auth needed for market data; places NOTHING."""
import sys
from collections import defaultdict

from bot import kalshi

K = kalshi


def _btc_spot():
    import requests
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price",
                         params={"symbol": "BTCUSDT"}, timeout=6)
        return float(r.json()["price"])
    except Exception:
        return None


# Real open BTC series on Kalshi (probed live). KXBTCD/KXBTC = threshold markets
# (Yes settles above strike); KXBTC15M = 15-min up/down; KXBTCMAXY = yearly max.
BTC_SERIES = ["KXBTCD", "KXBTC", "KXBTC15M", "KXBTCMAXY"]


def discover():
    """Open markets per known BTC series."""
    by_series = {}
    for s in BTC_SERIES:
        try:
            ms = K._markets(s)
        except Exception:  # noqa: BLE001
            ms = []
        if ms:
            by_series[s] = ms
    return by_series


def book_depth(ticker):
    """Raw resting depth: (yes_levels, no_levels, yes_contracts, no_contracts)."""
    try:
        ob = (K._get(f"/markets/{ticker}/orderbook") or {}).get("orderbook") or {}
    except Exception as e:  # noqa: BLE001
        return None, None, 0, 0, str(e)[:60]
    y = ob.get("yes") or []
    n = ob.get("no") or []
    yc = sum(int(l[1]) for l in y)
    nc = sum(int(l[1]) for l in n)
    return y, n, yc, nc, ""


def main():
    spot = _btc_spot()
    print(f"BTC spot ~${spot:,.0f}" if spot else "BTC spot unknown")
    series = discover()
    if not series:
        print("No open BTC markets found.")
        return
    print(f"\nDiscovered {len(series)} BTC series (by event prefix):")
    for s in sorted(series):
        print(f"  {s:<16} {len(series[s])} open markets")

    # For each series, sample up to 6 markets nearest the spot strike and probe books.
    for s in sorted(series):
        mkts = series[s]
        def near(m):
            st = K._strike(m)
            return abs((st or 0) - (spot or 0)) if spot else 0
        sample = sorted(mkts, key=near)[:6]
        print(f"\n=== {s}  ({len(mkts)} open; sampling {len(sample)} near-money) ===")
        any_depth = False
        for m in sample:
            t = m.get("ticker")
            st = K._strike(m)
            yb, nb, yc, nc, err = book_depth(t)
            lt, _ = K._last_trade(t)
            if err:
                print(f"  {t:<34} ERR {err}")
                continue
            best_y = max(yb, key=lambda l: l[0])[0] if yb else None
            best_n = max(nb, key=lambda l: l[0])[0] if nb else None
            depth = f"YES bids:{yc:>4}c@best {best_y}  NO bids:{nc:>4}c@best {best_n}"
            note = "" if (yc or nc) else "  <empty>"
            if yc or nc:
                any_depth = True
            strike = f"${st:,.0f}" if st else "updown"
            lts = f"{lt:.2f}" if lt is not None else "—"
            print(f"  {t:<34} {strike:<10} last={lts}  {depth}{note}")
        print(f"  -> {s}: {'HAS resting depth' if any_depth else 'BOOKS EMPTY'}")


if __name__ == "__main__":
    main()
