"""market-order-entry — "Enter at market, not with stop orders" (TTrades own voice).

Batch entry_own_04a. Recorded UNTESTABLE; reason below.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

REASON = (
    "Order-type / execution-mechanics claim, not a price-pattern claim. The rule adds no "
    "signal: it says HOW to fill an already-printed trigger (market order, not a buy/sell-stop; "
    "options: take the market unless price drops fast, then work the mid; ignore platform lag "
    "on >=15m). (1) concept_lab's locked entry convention (entry_mode='next_open', the open of "
    "the first M1 bar after the trigger closes) IS a market order, and entry_mode is a locked "
    "knob, so any book built here would test the trigger (CISD/closure — already covered by "
    "their own concepts and by phase 3's null rung 0), not the order type. (2) Every stated "
    "measurable — slippage between trigger close and fill, market-vs-mid fill quality on fast "
    "drops, TradingView execution lag — needs broker fills, bid/ask quotes or option chains; "
    "the certified data is mid-price XAUUSD M1 OHLC with no spread, depth or fill records. "
    "(3) The options branch has no gold instrument here at all.")

if __name__ == "__main__":
    p = cl.write_untestable(
        "market-order-entry", REASON, script=__file__,
        operationalization={"rules": [
            "not operationalisable: order-type choice on an existing trigger; the harness "
            "entry is already a market fill at the next M1 open (locked)",
            "measurables (slippage, mid vs market fill quality, platform lag) need fill/quote "
            "data absent from mid-price M1 OHLC"], "params": {}},
        notes="Method spec §4.8 also records an unreconciled OCO resting-limit statement "
              "(oco-bracket-order); the two order types are not reconciled in the corpus.")
    print(p)
