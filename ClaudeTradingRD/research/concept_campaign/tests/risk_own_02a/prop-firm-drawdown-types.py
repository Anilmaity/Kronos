"""risk_own_02a / prop-firm-drawdown-types — UNTESTABLE (account-rule definitions, not a market claim)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("an enumeration of prop-firm account mechanics (static; trailing end-of-day; trailing "
          "unrealised; daily-loss-limit plus trailing maximum-loss-limit), i.e. definitions of how a "
          "firm computes a breach floor. It makes no claim about XAUUSD price: every rule is true by the "
          "firm's contract, and its only 'measurable' (breach probability of one trade sequence under "
          "each type) is a Monte Carlo property of a given strategy's P&L path under firm-specific "
          "terms, not something a trade/gate/rate test on gold OHLC can confirm or refute. The one "
          "decidable-looking statement ('identical realised P&L can pass EOD-trailing and fail "
          "unrealised-trailing') holds by construction whenever MAE differs.")
if __name__ == "__main__":
    print(cl.write_untestable("prop-firm-drawdown-types", REASON, script=__file__,
                              notes="Companion sizing concept prop-firm-drawdown-sizing was recorded UNTESTABLE in risk_own_01b for the same reason."))
