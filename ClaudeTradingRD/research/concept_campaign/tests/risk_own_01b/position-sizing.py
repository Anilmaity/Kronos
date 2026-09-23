"""risk_own_01b / position-sizing — UNTESTABLE (pure sizing arithmetic)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("pure position-sizing arithmetic: risk_per_trade = drawdown_allowance / N "
          "(N = consecutive losses to survive, 10-15 / ~7 / 1-3 / 15-20) and a reduced "
          "size for open entries with an uncomfortable stop. Neither reading makes a "
          "claim about XAUUSD price behaviour: sizing scales every trade's R by a "
          "constant, so it cannot change any entry's control-adjusted expectancy, and "
          "the survival arithmetic (N losses before the drawdown) is true by "
          "construction for any strategy. What it would need is a specific strategy's "
          "loss-streak distribution plus a prop firm's drawdown rules (a Monte Carlo on "
          "someone's book), not a hypothesis about gold that OHLC can falsify. The "
          "'reduced size at the open' variant has no stated multiplier and also only "
          "rescales R.")
if __name__ == "__main__":
    p = cl.write_untestable("position-sizing", REASON, script=__file__,
                            notes="Both variants (10-15 vs 7 divisor; $1,500/10 losses) are the "
                                  "same arithmetic with a different dial; one record covers both.")
    print(p)
