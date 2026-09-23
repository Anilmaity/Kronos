"""nq-over-es-volatility-preference (AM Trades, guest): trade NQ by default, switch to ES only
when ES has been clearly weaker all week and the setup is a short.

UNTESTABLE on this dataset: the rule is an instrument choice between two equity-index futures
(NQ vs ES). The campaign's certified data is XAUUSD M1 only; there is no second correlated
instrument, so neither 'default to the more volatile one' nor 'switch to the relatively
weaker one' can be evaluated, and substituting another pair would test a different rule.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

if __name__ == "__main__":
    print(cl.write_untestable(
        "nq-over-es-volatility-preference",
        "needs a second, correlated instrument: the rule chooses between NQ and ES futures by "
        "relative volatility/weekly relative weakness; the certified dataset is single-instrument "
        "XAUUSD M1, so there is nothing to choose between and no ES/NQ series to score",
        script=__file__))
