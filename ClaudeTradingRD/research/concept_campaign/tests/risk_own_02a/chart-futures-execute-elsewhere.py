"""risk_own_02a / chart-futures-execute-elsewhere — UNTESTABLE (vehicle selection; the other vehicles are absent)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("a vehicle-selection rule: frame on the overnight-inclusive futures chart (ES/NQ/GC, minis) and "
          "route the order to an ETF, index option or ETF option (or avoid single stocks). The claim is a "
          "comparison between instruments -- futures vs SPY/QQQ/option charts, minis vs micros, futures vs "
          "CFD for gold -- and the certified data holds one series (XAUUSD spot, already overnight-inclusive), "
          "so there is no second vehicle whose levels, signals, fills or spreads could be compared. Rebuilding a "
          "'cash-session-only' view of the same spot series would not be the ETF (different instrument, "
          "prices and gaps) and, against a baseline book that is itself null (phase 3 rung 0), a difference "
          "between two books could not be attributed to the vehicle.")
if __name__ == "__main__":
    print(cl.write_untestable("chart-futures-execute-elsewhere", REASON, script=__file__,
                              notes="Mixed voice (host + Trade For Opportunity guest); both variants are vehicle choices."))
