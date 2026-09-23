"""ttfm-indicator-settings — UNTESTABLE.

The concept is the settings panel of a paywalled TradingView indicator (history count,
C2/C3/C4 toggles, colours, offsets, time-filter UI mechanics). Its only trading content —
which C2/C3/C4 prints qualify — is explicitly withheld ("I go over all the requirements for
these within my course and mentorship", CqMIh-Vvhbg), so the indicator's prints cannot be
reproduced from the free material and its two measurables (agreement with a hand-coded C2
detector; grey/red/orange outcome shares) need the indicator's own output, which we do not have.
The fractal-model logic the indicator plots is tested under its own concept ids
(fractal-model-c2/c3/c4, ttfm-favorite-daily-4h-15m).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

if __name__ == "__main__":
    p = cl.write_untestable(
        "ttfm-indicator-settings",
        "Indicator UI/settings description, not a trading rule: the C2/C3/C4 print "
        "requirements it encodes are paywalled (withheld for the course, CqMIh-Vvhbg), so "
        "its prints cannot be reproduced from OHLC; both stated measurables (agreement with "
        "the indicator's C2 print; grey/red/orange outcome distribution) require the "
        "proprietary indicator's own output. Display settings (offsets, colours, history "
        "count, time-filter hour-rounding) carry no market claim.",
        script=__file__,
        notes="The model logic it draws is tested under fractal-model-* and "
              "ttfm-favorite-daily-4h-15m.")
    print(p)
