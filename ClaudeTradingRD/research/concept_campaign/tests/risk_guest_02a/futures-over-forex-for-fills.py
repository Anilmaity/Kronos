"""futures-over-forex-for-fills — UNTESTABLE (batch risk_guest_02a)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = "An instrument-comparison claim: a resting limit at an exact breaker level fills on futures but can miss on a spread-quoted forex feed. Testing it needs the same setups on two feeds (e.g. COMEX GC futures and a bid/ask-quoted XAUUSD, or the guest's GBPUSD vs 6B) with spreads; the certified dataset is a single XAUUSD M1 OHLC mid series with no bid/ask spread and no futures counterpart, so neither fill rate can be computed."

if __name__ == "__main__":
    p = cl.write_untestable("futures-over-forex-for-fills", REASON, script=__file__)
    print(p)
