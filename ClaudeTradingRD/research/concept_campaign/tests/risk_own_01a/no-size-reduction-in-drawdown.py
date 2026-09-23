"""no-size-reduction-in-drawdown — UNTESTABLE in an R-based harness.

The concept is sizing arithmetic: on a fixed-2R strategy, halving risk after a loss means
the next winner only restores break-even, while constant risk puts you 1R ahead; scaling
by recent outcome "adds another variable". Position size scales the dollar value of a
trade, never its R outcome, so every trade_test / gate_test / rate_test returns the same
numbers with or without the rule. The concept also asserts no directional market effect
(it does not say post-loss trades are better or worse, only that sizing should ignore
them), so there is no claim to orient a gate test on. The 34% break-even figure is the
identity 1/(1+2) and needs no data.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl  # noqa: E402

if __name__ == "__main__":
    p = cl.write_untestable(
        "no-size-reduction-in-drawdown",
        "Pure position-sizing arithmetic: constant vs outcome-scaled dollar risk changes "
        "equity-curve dollars, never any trade's R outcome, so no R-based test (trade, gate "
        "or rate) can distinguish it from the baseline; the concept asserts no directional "
        "market effect (e.g. that post-loss trades differ) to orient a gate on, and its "
        "34% break-even at 2R is the arithmetic identity 1/(1+2).",
        script=__file__,
        notes="Its empirical premise (post-loss trade expectancy equals unconditional "
              "expectancy) is a different, undirected hypothesis the concept never states.")
    print("wrote", p)
