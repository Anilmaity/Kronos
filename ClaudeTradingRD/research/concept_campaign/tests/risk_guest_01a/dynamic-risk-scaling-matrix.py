"""dynamic-risk-scaling-matrix (guest: Trader Kane) - gate_test on the sequential book.

Concept: risk 1%, +0.5% after each winner, -0.5% after each loser, cap 2%, floor 0.25%;
the purpose is to exploit streaks (bigger after wins, smaller after losses). Sizing is
R-invariant per trade, so the ladder can only beat flat 1% if outcomes are serially
dependent: trades that follow a winner (sized UP) must have higher expectancy per R than
trades that follow a loser (sized DOWN). That first-order dependency is what every step
of the ladder bets on, and it is the testable content of the rule.

Gate `after_win` = the previous taken trade (sequential book, resolved before this
decision) closed with gross R > 0. Complement = previous trade lost (or was flat / none).
claim '+'. The ladder's cap/floor arithmetic and the prop-account framing are sizing
arithmetic and not scored.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl   # noqa: E402
import _book as bk         # noqa: E402

CID = "dynamic-risk-scaling-matrix"
TOD_TOL = 30


def detect(m1):
    ev = bk.chain(m1)
    ev["after_win"] = ev["prev_outcome"] == 1
    return bk.public(ev, ["prev_outcome", "after_win"])


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_prevwin", lambda: detect(cl.load_m1()), version=bk.VERSION)
    print(len(ev), ev["after_win"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, "after_win", mask_available_at="decision_time",
                       max_hold="150min", ctrl_tod_tol_min=TOD_TOL, claim="+")
    for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": bk.BASE_RULES + [
        "gate after_win: the previous taken trade closed with gross R > 0 (the ladder "
        "steps risk UP); complement = previous trade lost / flat / none (ladder steps "
        "DOWN or holds); claim '+'",
        "ladder arithmetic (1% base, +/-0.5%, cap 2%, floor 0.25%) is sizing, not scored"],
        "params": {**bk.BASE_PARAMS, "step_trigger": "previous trade outcome",
                   "ctrl_tod_tol_min": TOD_TOL}}
    src = {**bk.BASE_SOURCES,
           "step_trigger": "corpus: 1wKfc2gN4xg 'I risk 1%, if I'm on a win streak, I risk "
                           "more' (per-outcome stepping, yaml detection_rules)",
           "ctrl_tod_tol_min": "declared-before-run: not a timing rule; hold the NY "
                               "clock in the control (README trap 9)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Baseline = sequential 15m bare CISD book (see _book.py). "
                              "Tests the serial dependence the ladder bets on; a NULL "
                              "means sizing off the last outcome adds variance, not "
                              "expectancy, on this book.")
    print(p)
