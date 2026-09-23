"""risk_own_01b / prop-firm-drawdown-sizing — UNTESTABLE (sizing / account-economics arithmetic)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("sizing and prop-account economics, not a market claim: effective_capital := "
          "max_drawdown, risk_per_trade := 0.5-1% of nominal or 5% / 7-10% / 20-50% of the "
          "drawdown, required_return := profit_target / max_drawdown, and offer comparison "
          "by evaluation+activation fee. Every rule is arithmetic that holds by construction "
          "(a fixed fraction of the drawdown gives a fixed number of losers of runway) or "
          "depends on a firm's fee/drawdown terms (static vs trailing, daily loss limits), "
          "none of which is in XAUUSD OHLC. Scaling risk rescales R uniformly and cannot "
          "change a book's control-adjusted expectancy, so no trade/gate/rate test on gold "
          "can decide it. The measurables it lists (ruin probability per tier, pass rate, "
          "time-to-pass) are Monte Carlo properties of a given strategy's R distribution "
          "under a firm's rules, not falsifiable claims about the instrument.")
if __name__ == "__main__":
    p = cl.write_untestable("prop-firm-drawdown-sizing", REASON, script=__file__,
                            notes="All three variants (Trader T 0.5%/1% of nominal; money-vs-time "
                                  "tiers of the drawdown; drawdown-to-target ratio when buying) "
                                  "are arithmetic; one record covers them.")
    print(p)
