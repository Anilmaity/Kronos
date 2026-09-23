"""incremental-size-scaling — UNTESTABLE (batch risk_guest_02a)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = "Pure position-sizing / account-capital advice (open at $500-1,000, step size in micro-contract increments, halve size when panicking). Per-trade R outcomes on XAUUSD OHLC are invariant to contract count, so no test of R can distinguish scaling schedules; the only stated triggers ('earned', 'panic', 'comfortable level') are subjective and the measurables (rule-break rate, self-reported anxiety) need a trader's journal, not price data."

if __name__ == "__main__":
    p = cl.write_untestable("incremental-size-scaling", REASON, script=__file__)
    print(p)
