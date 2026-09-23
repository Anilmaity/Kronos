"""oco-bracket-order — UNTESTABLE: order-type mechanics with no directional or edge claim.

Batch entry_own_04b. The concept (dtsrR8dX2Ro) names the order type he uses: a resting
limit entry bracketed by a stop-loss and take-profit as one-cancels-the-other. It makes no
claim that a setup, filter or level predicts anything; its two 'measurables' (limit fill rate
vs market entry; slippage on the stop leg) are execution-quality questions.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("Order-type mechanics, not a trading claim: 'limit in, stop+target as an OCO pair, "
          "whichever fills cancels the other'. It asserts no direction, level or filter that "
          "could beat a control. The harness already resolves every trade as an OCO bracket "
          "(stop and target both resting, first touched wins on M1), so the bracket itself has "
          "no counterfactual to compare against. The listed measurables need data we lack: "
          "stop-leg slippage needs broker fills / bid-ask ticks (one mid-quote M1 series, stops "
          "fill at the level or the gap-open by construction), and 'limit fill rate vs market "
          "entry' has no stated limit placement rule (ambiguity: 'No rule is given for where the "
          "limit is placed relative to the setup level'), so there is no book to fill.")

if __name__ == "__main__":
    p = cl.write_untestable("oco-bracket-order", REASON, script=__file__)
    print(p)
