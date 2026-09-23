"""stop-moves-when-adding (guest: Ben TT / NickDoesFutures; contested) -> UNTESTABLE, 2 readings."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

A = ("Reading a (Ben: on adding a second tranche, move the first tranche's stop to break even "
     "or to the second tranche's stop): the rule is conditional on an add whose trigger is "
     "never stated (yaml ambiguity 'what triggers the second entry is not stated'), with no "
     "tranche size ratio, so the blended entry and break-even price are undefined. Choosing an "
     "add trigger ourselves would test an invented scaling model, not his rule; the stop move "
     "on its own is the separate break-even-management concept. (The harness also scores one "
     "fixed stop per trade, so a mid-trade stop move cannot be expressed as a single event.)")
B = ("Reading b (NickDoesFutures variant: any add must be accompanied by a stop move so total "
     "open risk never exceeds the initial risk; adding without moving is a plan violation): a "
     "risk-accounting identity/plan-consistency rule. It asserts nothing about price and has "
     "no chart condition, and where the stop moves to is explicitly unspecified.")
cl.write_untestable("stop-moves-when-adding", A, reading="a", script=__file__)
cl.write_untestable("stop-moves-when-adding", B, reading="b", script=__file__)
print("written")
