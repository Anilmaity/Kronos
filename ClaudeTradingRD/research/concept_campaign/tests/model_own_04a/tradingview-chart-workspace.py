"""tradingview-chart-workspace — UNTESTABLE (batch model_own_04a)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("A charting-workspace configuration (TradingView colours, #F5F5F5 background, templates, "
          "drawing presets, keyboard shortcuts, object-tree hygiene). It makes no claim about price: "
          "no entry, level, time or outcome is asserted, and its own 'measurable' field says it is not "
          "market-measurable. The only parts that change the candles read (New York time with DST, "
          "full electronic session, continuous-contract adjust on / settlement off) are already fixed "
          "in the harness as settled conventions (America/New_York DST, 18:00 NY daily roll, certified "
          "continuous XAUUSD M1), so there is nothing left to vary and no outcome to score.")

if __name__ == "__main__":
    print(cl.write_untestable("tradingview-chart-workspace", REASON, script=__file__))
