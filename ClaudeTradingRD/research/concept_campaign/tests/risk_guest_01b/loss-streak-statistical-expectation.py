"""loss-streak-statistical-expectation (guest: STRATalorian) -> UNTESTABLE (combinatorics)."""
import sys, math
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

# Expected longest losing run in N Bernoulli trials ~ log_{1/q}(N*p) (Schilling); notes only.
N = 1000
ex = {w: math.log(N * w) / math.log(1 / (1 - w)) for w in (0.3, 0.4, 0.5, 0.6, 0.7)}
chk = ", ".join(f"win {int(w*100)}%: ~{v:.1f}" for w, v in ex.items())
REASON = ("A combinatorial statement about losing-run length over 1,000 trades plus sizing and "
          "psychology advice. The run length is a function of the (unstated) win rate and of "
          "trade independence, not of anything in price; there is no concept-specific event "
          "whose edge vs a matched control could be measured, so none of trade/gate/rate test "
          "applies. The sizing rule (survive 5-10 full-risk losses) is pure arithmetic.")
cl.write_untestable("loss-streak-statistical-expectation", REASON, script=__file__,
                    notes=("Arithmetic context (i.i.d. trades, N=1000, expected longest losing "
                           "run): " + chk + ". So '5-10 in a row' holds for win rates of roughly "
                           "45-70%; at the typical 1R:2R book win rate (~33%) runs of 13+ are "
                           "expected. Not a market claim."))
print(chk)
