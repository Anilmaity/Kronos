"""timeframe-pairing, update_20261007_live_02 (u1007a): the 5m swing -> 15s execution pair -> UNTESTABLE.

Prior readings a/b (1h->5m pairing) are untouched; this tests ONLY the new 5m/15s claim.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("The new claim is the 5-minute swing point -> 15-second execution pair (h1ZQWWQDhKA: "
          "'if you want to trade the 15-second model, that would be a five minute swing point, "
          "15 second'). Its defining step (the 15s CISD/entry and 15s protected-swing stop) needs "
          "sub-minute bars; the certified XAUUSD data is M1 only, so neither the entry nor the stop "
          "can be located or resolved (same reason as fifteen-second-execution-timeframe__b). The "
          "companion statement 'there's always a fractal model, it's just depending on the time "
          "frame' is an unfalsifiable search instruction (drop to whichever pair shows a model), "
          "not a rule with a fixed event; testing it would be a timeframe search, which the "
          "campaign forbids. The M1-resolvable pairs (1h->5m) are already readings a and b.")
cl.write_untestable("timeframe-pairing", REASON, reading="u1007a", script=__file__,
                    notes="Source also says nothing would work in price like that day's, so the "
                          "'always a model' line is not an endorsement (draft ambiguities).")
print("written")
