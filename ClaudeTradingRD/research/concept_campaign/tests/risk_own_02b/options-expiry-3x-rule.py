"""options-expiry-3x-rule — UNTESTABLE on XAUUSD spot OHLC (batch risk_own_02b).

Reason recorded below. No detector, no test run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

CID = "options-expiry-3x-rule"
REASON = ("Option-expiry selection rule (buy expiry at 3x the estimated time-to-target to limit theta). The claim is about option premium decay versus holding time. That needs option prices or implied volatility, which the campaign lacks (XAUUSD spot M1 only). The corpus also gives no method for the time-to-target estimate the rule scales.")
NOTES = ("A realised time-to-target distribution on spot could be computed, but it would not test the claim (that 3x expiry beats short-dated options net of theta) without option P&L. The corpus marks the rule 'Not applicable - a sizing / instrument rule'.")

if __name__ == "__main__":
    p = cl.write_untestable(CID, REASON, script=__file__, notes=NOTES)
    print("wrote", p)
