"""zero-dte-strike-selection (Alex's Options, guest): choose a 0DTE strike that is in the money
at T1 and pay < half its intrinsic value at T1, so T1 = +100%.

UNTESTABLE on OHLC: the rule is option-premium arithmetic. Whether the price condition is
available at entry, and the realised contract return, depend on the option chain (premium,
implied volatility, bid/ask, theta between entry and target), none of which exists for this
dataset. The underlying's move to T1 is not what the rule adds -- the entry/target come from
the chart setup, tested under their own concepts.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

if __name__ == "__main__":
    print(cl.write_untestable(
        "zero-dte-strike-selection",
        "options-pricing rule: requires same-day-expiry option chain data (premiums, IV, bid/ask, "
        "theta) to know whether a strike trades below half its intrinsic value at T1 and what the "
        "contract returns; only underlying XAUUSD OHLC is available, and the underlying's "
        "entry/target belong to the separate chart-setup concepts",
        script=__file__))
