"""dxy-yields-smt-pair (guest: Day Trading Rauf) -> UNTESTABLE.

The concept pairs the Dollar Index with the bond / yield chart: rising yields
corroborate a rising dollar, and a DXY-vs-yields divergence at a swing reads
accumulation in the DOLLAR. It needs a DXY series and a Treasury yield (or bond
futures) series; neither exists in the campaign's data (certified XAUUSD M1 plus
XAG/EUR H1/D1 correlates). EURUSD is not DXY and there is no yield proxy at all.
The concept is also a statement about DXY, not gold, and it never says whether
the bond chart is PRICE or YIELD, which inverts the divergence reading.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("Needs a DXY series and a Treasury yield / bond-futures series on the same bars; "
          "the campaign holds only XAUUSD M1 and XAG/EURUSD H1/D1 correlates, with no dollar "
          "index and no rates data (EURUSD is one DXY component, not DXY, and nothing proxies "
          "yields). The claim is about DXY, not gold, and the source never says whether the "
          "bond chart is price or yield, which inverts the divergence sign - so even the "
          "direction of the test is undefined without that choice.")

if __name__ == "__main__":
    p = cl.write_untestable("dxy-yields-smt-pair", REASON, script=__file__)
    print(p)
