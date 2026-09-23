"""trade-frequency-under-two-per-day (guest: AM Trades) - UNTESTABLE.

The concept records an observed average ("probably taking less than two a day", ~8 a
week) of one trader's discretionary market-maker-model trading on indices and Bitcoin.
The yaml is explicit that it is "an output of the model rather than an enforced cap" and
gives no per-day maximum. There is therefore no selection rule to gate a book on: the
only rules ("expect fewer than two per day", "take no trades when the model does not
present") are a description of a model we do not have, not a filter on one we do.
Any cap-based operationalisation would test a claim he explicitly does not make; the
cap readings are tested under daily-trade-cap-risk-envelope (3/day) and
risk-limits-and-trade-frequency (b: 1/day, 2/week).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

if __name__ == "__main__":
    p = cl.write_untestable(
        "trade-frequency-under-two-per-day",
        "descriptive frequency observation, not a rule: the guest states ~<2 trades/day "
        "(~8/week) as an OUTPUT of his discretionary MMXM model on indices/BTC and "
        "explicitly not an enforced cap, so there is no decision rule to gate a gold book "
        "on; turning it into a cap would test a claim he does not make (caps are tested "
        "under daily-trade-cap-risk-envelope and risk-limits-and-trade-frequency b)",
        script=__file__)
    print(p)
