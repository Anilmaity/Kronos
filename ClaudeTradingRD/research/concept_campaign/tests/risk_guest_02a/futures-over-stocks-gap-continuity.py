"""futures-over-stocks-gap-continuity — UNTESTABLE (batch risk_guest_02a)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = "An instrument-selection claim that cash equities/ETFs gap overnight so their daily profile is unreadable while futures daily candles open at the prior close. It is a comparison between asset classes; the campaign has only XAUUSD M1 (a near-continuous 23h market with no cash-equity or ETF counterpart), so neither the gap incidence across instrument classes nor futures-vs-ETF profile agreement can be measured. Gold's own small gaps would describe gold, not the claim."

if __name__ == "__main__":
    p = cl.write_untestable("futures-over-stocks-gap-continuity", REASON, script=__file__)
    print(p)
