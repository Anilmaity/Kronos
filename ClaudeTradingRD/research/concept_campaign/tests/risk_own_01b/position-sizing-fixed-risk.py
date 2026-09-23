"""risk_own_01b / position-sizing-fixed-risk — UNTESTABLE (sizing arithmetic)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("fixed-dollar (or fixed-%) risk per trade with contracts = risk / (value_per_point "
          "x stop_points) is a sizing procedure, not a claim about price. Its stated "
          "justification (the win-rate vs R table only holds under constant risk; a "
          "-1R,-1R,+4R sequence at fixed contracts loses money) is arithmetic that is true "
          "for any trade list, and the campaign harness already measures every book in R, "
          "i.e. under exactly this constant-risk convention, so there is no alternative "
          "arm on gold OHLC to test it against. The $100 / 4%-of-drawdown / 1% figures and "
          "the 13-days-to-pass report are personal account facts, and micro-vs-mini "
          "rounding is a futures contract-spec detail absent from XAUUSD spot data.")
if __name__ == "__main__":
    p = cl.write_untestable("position-sizing-fixed-risk", REASON, script=__file__,
                            notes="Stop placement 'from the chart' is covered by the stop "
                                  "concepts (stop-loss-placement, protected-swing), not here.")
    print(p)
