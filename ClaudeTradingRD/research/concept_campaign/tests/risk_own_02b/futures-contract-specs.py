"""futures-contract-specs — UNTESTABLE on XAUUSD spot OHLC (batch risk_own_02b).

Reason recorded below. No detector, no test run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

CID = "futures-contract-specs"
REASON = ("Contract-specification arithmetic (point = handle, 4 ticks per ES point, NQ $20/pt, MNQ $2/pt, P&L = points x multiplier x contracts, whole-contract partials, CFD->futures symbol mapping). It is a units definition, not a claim about price, so there is no directional hypothesis for trade/gate/rate tests to decide; the harness scores in R, where multipliers cancel.")
NOTES = ("Pure sizing/units arithmetic, which the batch rules route to write_untestable. The 'measurable' items (P&L reconciliation with the multipliers; how often <2 contracts blocks partials) are bookkeeping identities, not market hypotheses.")

if __name__ == "__main__":
    p = cl.write_untestable(CID, REASON, script=__file__, notes=NOTES)
    print("wrote", p)
