"""volume-spike-at-extremes (guests: Alex's Options, Trade For Opportunity) -> UNTESTABLE.

The concept is a volume rule on sub-minute futures charts (15s/30s/1m): a volume
spike while price falls marks demand, a spike while it rises marks supply, acted
on when it coincides with a stop hunt. The certified XAUUSD data is OANDA M1 OHLC
with NO volume column (checked: columns open/high/low/close in every XAU parquet
under ClaudeTradingRD), no sub-minute bars, and spot gold is OTC with no
exchange volume. Substituting M1 range for volume would test a different
(range-expansion) concept, not this one.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("Needs traded volume on 15s/30s/1m bars of a volume-bearing (futures) instrument. "
          "Every XAUUSD file in the workspace (certified xau_m1_full.parquet and the others) "
          "carries open/high/low/close only - no volume or tick-count column - and has no "
          "sub-minute bars; spot gold is OTC with no exchange volume. 'Spike' is also never "
          "sized. Replacing volume with M1 range would test range expansion, a different "
          "concept, so no faithful operationalisation exists on this data.")

if __name__ == "__main__":
    p = cl.write_untestable("volume-spike-at-extremes", REASON, script=__file__)
    print(p)
