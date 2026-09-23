"""orderflow-narrows-ict-entry (guest: HolyAngelBruv) -> UNTESTABLE.

The concept's load-bearing step is the entry filter: at an ICT level, enter only when
the footprint / DOM shows the tape speeding up and aggression on the intended side.
The certified data is M1 OHLC for XAU_USD (spot CFD, OANDA) with no volume, no
bid/ask-classified trades, no tape and no depth of market. None of 'speed of the
tape', 'aggression' (delta) or DOM resting size can be reconstructed from OHLC, and
the guest gives no threshold even for those (read by eye). Substituting a bar-range
proxy would test a different rule, not this one.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("needs order-flow data we lack: the rule's only operative step is footprint/DOM "
          "confirmation (tape speed, buy/sell aggression, DOM) at the ICT level; the dataset is "
          "M1 OHLC of spot XAU_USD with no volume, no trade-side classification and no book, "
          "and the guest gives no numeric threshold (read by eye, DOM layer self-described as "
          "not mastered). An OHLC range/momentum proxy would be a different rule.")

if __name__ == "__main__":
    p = cl.write_untestable("orderflow-narrows-ict-entry", REASON, script=__file__,
                            notes="The ICT-context layer alone is not this concept; it is covered "
                                  "by the channel's own POI concepts.")
    print(p)
