"""bracket-order-not-guaranteed — UNTESTABLE (batch risk_guest_02a)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = 'An execution-quality claim (stop orders may not trigger / fill at the stop level). Deciding it needs broker order and fill records or bid/ask tick data; the harness has one mid-quote M1 OHLC series with no order book, spread or fill information, and by construction fills every stop at the stop (or the gap-open), so slippage beyond the stop is unmeasurable. The remaining advice (monitor the position, else reduce size) is behavioural.'

if __name__ == "__main__":
    p = cl.write_untestable("bracket-order-not-guaranteed", REASON, script=__file__)
    print(p)
