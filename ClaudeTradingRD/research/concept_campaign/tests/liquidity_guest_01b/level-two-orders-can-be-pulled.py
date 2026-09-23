"""level-two-orders-can-be-pulled (guest: HolyAngelBruv) -> UNTESTABLE.

The concept is a claim about depth-of-market data: displayed level-2 limit size
is withdrawn rather than filled as price approaches it, and executed flow
(tape/footprint) beats displayed size. Both measurables ('fill rate vs pull rate
of displayed size', 'predictive value of displayed size vs traded delta') need an
order-book / DOM history and trade-by-trade prints. The campaign's only data is
XAUUSD OANDA M1 OHLC (no volume column, no book, no trades), and the claim is
stated for ES futures specifically.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("Needs depth-of-market (level-2) snapshots and executed-trade prints: the claim "
          "is that displayed resting limit size is pulled rather than filled as price "
          "approaches, and that traded delta beats displayed size. The certified data is "
          "XAUUSD OTC M1 OHLC only (no volume, no order book, no tape; spot gold has no "
          "central book at all), and the guest scopes the claim to ES futures. Neither "
          "measurable (fill-vs-pull rate, displayed size vs delta) can be formed from OHLC.")

if __name__ == "__main__":
    p = cl.write_untestable("level-two-orders-can-be-pulled", REASON, script=__file__)
    print(p)
