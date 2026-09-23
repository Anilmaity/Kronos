"""weekly-profile-not-predicted-in-advance (guest: AM Trades, wGYde-h84cs).

Recorded UNTESTABLE. The concept is an epistemic posture ("I don't know what the
weekly profile is going to be ... I'm letting the chart paint it out for me"), not
a prediction rule. It gives no pre-week classifier whose accuracy could be scored,
and the "Monday-morning guess" in its `measurable` list is never specified, so any
guess we invented would test our invention, not the concept (and a NULL for it would
be vacuous: the concept *asserts* unpredictability). Its operative sub-rules are
separate concepts tested elsewhere: skip Monday (no-monday-rule) and confirm the
profile with an hourly CISD at the manipulation (hourly-cisd-manipulation-confirmation);
the profile set itself is "not enumerated in this video" (YAML ambiguities).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("epistemic posture with no decision rule: the concept only says the weekly "
          "profile is not assigned before the week trades; it names no pre-week "
          "classifier to score (the 'Monday-morning guess' is unspecified and the "
          "profile set is not enumerated in wGYde-h84cs), so no OHLC statistic can "
          "confirm or refute it; its operative parts (skip Monday; confirm by hourly "
          "CISD at the manipulation) are the separate concepts no-monday-rule and "
          "hourly-cisd-manipulation-confirmation")

if __name__ == "__main__":
    p = cl.write_untestable("weekly-profile-not-predicted-in-advance", REASON,
                            script=__file__)
    print(p)
