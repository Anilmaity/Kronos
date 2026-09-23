"""futures-contract-rollover — UNTESTABLE on XAUUSD spot OHLC (batch risk_own_02b).

Reason recorded below. No detector, no test run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

CID = "futures-contract-rollover"
REASON = ("Instrument-selection procedure for quarterly index futures (ES/NQ): roll to whichever contract has the most open interest and volume on barchart.com, chart the back-adjusted continuous contract. It makes no claim about price behaviour, and the data it needs (per-contract open interest and volume across a futures curve) does not exist for the XAUUSD spot/OANDA M1 series, which has no contracts and no rolls.")
NOTES = ("The concept's own invalidation line says 'Not applicable - a data / instrument selection procedure'. Its measurables (rule-roll dates vs exchange roll dates; level differences between roll methods) need a futures curve with OI/volume, which the campaign data lacks.")

if __name__ == "__main__":
    p = cl.write_untestable(CID, REASON, script=__file__, notes=NOTES)
    print("wrote", p)
