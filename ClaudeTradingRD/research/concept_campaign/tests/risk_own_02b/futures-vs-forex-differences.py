"""futures-vs-forex-differences — UNTESTABLE on XAUUSD spot OHLC (batch risk_own_02b).

Reason recorded below. No detector, no test run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

CID = "futures-vs-forex-differences"
REASON = ("Vehicle-choice argument (futures have exchange bid/ask with no broker-widened spread or slippage, no PDT rule, different tax, lots->contracts vocabulary). Testing it needs executed fills or quote/tick data from both a futures venue and a forex broker on the same setups. The campaign has one OHLC mid-price series with no bid/ask, fills or futures quotes. Also, cost cancels exactly in the harness's control-matched differential, so a spread assumption cannot move any verdict.")
NOTES = ("Measurables are realised slippage futures vs spot (needs fills), and expectancy under different spread assumptions (arithmetic: with a matched control the cost term cancels in diff, so it is not a market hypothesis). PDT and tax are regulatory, not price facts.")

if __name__ == "__main__":
    p = cl.write_untestable(CID, REASON, script=__file__, notes=NOTES)
    print("wrote", p)
