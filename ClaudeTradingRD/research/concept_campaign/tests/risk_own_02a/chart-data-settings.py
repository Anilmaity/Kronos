"""risk_own_02a / chart-data-settings — UNTESTABLE (futures data-feed configuration; no alternate series)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("a futures chart-configuration rule (back-adjust ON, settlement OFF, ETH not RTH, minis not "
          "micros, CME feed, NY timezone). The certified data is a single continuous XAUUSD spot M1 series: "
          "it has no contract rolls to back-adjust, no exchange settlement price to toggle, no mini/micro "
          "pair and no CME feed, so neither side of any toggle exists to compare. The one setting that does "
          "apply (New York time with DST, 18:00 roll) is already the harness convention, settled empirically "
          "in session_window_fit, and is not a claim with an outcome. The listed measurables (candles or level "
          "breaks that differ between adjusted/unadjusted or settlement on/off series) need those alternate "
          "futures series, which we do not have.")
if __name__ == "__main__":
    print(cl.write_untestable("chart-data-settings", REASON, script=__file__,
                              notes="All four contested variants concern the same data-configuration toggles; one record covers them."))
