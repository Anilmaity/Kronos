"""daily-trade-cap-risk-envelope (guest: Trade For Opportunity) - gate_test.

Concept: at most three trades per day at ~1% risk and ~2:1, so the day is bounded at
-3% / +6%; stop when the trade count is spent. The envelope arithmetic itself is
tautological (3 x 1% risk); the testable content is the corpus's own measurable:
"expectancy of the trades within the cap vs those beyond it" - i.e. do the trades the
cap lets you take beat the ones it makes you skip?

Gate (declared before run): in_cap = the trade is the 1st, 2nd or 3rd taken trade of
its trading day (18:00 NY roll) in the sequential baseline book. claim '+': in-cap
trades are better (control-adjusted) than the 4th+ trades the cap forbids.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl   # noqa: E402
import _book as bk         # noqa: E402

CID = "daily-trade-cap-risk-envelope"
CAP = 3
TOD_TOL = 30


def detect(m1):
    ev = bk.chain(m1)
    ev["in_cap"] = ev["day_rank"] <= CAP
    return bk.public(ev, ["day_rank", "in_cap"])


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_cap{CAP}", lambda: detect(cl.load_m1()), version=bk.VERSION)
    print(len(ev), ev["in_cap"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, "in_cap", mask_available_at="decision_time",
                       max_hold="150min", ctrl_tod_tol_min=TOD_TOL, claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties", "gate"):
        print(k, res.get(k))
    op = {"rules": bk.BASE_RULES + [
        f"gate in_cap: trade is among the first {CAP} taken trades of its trading day "
        "(18:00 NY roll); complement = the 4th+ trades the cap forbids",
        "1% risk / -3% .. +6% envelope is sizing arithmetic, R-invariant: not scored"],
        "params": {**bk.BASE_PARAMS, "cap_per_day": CAP, "day_roll": "18:00 NY",
                   "ctrl_tod_tol_min": TOD_TOL}}
    src = {**bk.BASE_SOURCES,
           "cap_per_day": "corpus: 0bH_kkG2q6s 'i limit myself to about uh three trades per day'",
           "day_roll": "session_window_fit: settled 18:00 NY daily roll",
           "ctrl_tod_tol_min": "declared-before-run: the cap is not a timing rule but "
                               "in-cap trades cluster early in the trading day "
                               "(README trap 9), so the control holds the NY clock"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Baseline = sequential 15m bare CISD book (see _book.py). "
                              "Re-run ONCE after fixing a bug in _book.py (found by the size-down-on-fear b probe): a clock-hold time exit whose hold ended inside the 17:00 NY halt freed the position slot at the last pre-halt bar instead of at the hold's wall-clock end. Second fix + re-run: same-bar opposite CISD pairs (4 of 32,827) given a deterministic order (the probe of size-down-on-fear b caught slice-dependent order). Second run before this fix: NULL, diff +0.0223 [-0.0085, +0.0526]. First (buggy-chain) run: NULL, diff +0.0186 [-0.0123, +0.0516]. "
                              "Break-even trades count toward the cap (ambiguity "
                              "resolved: every taken trade is a slot).")
    print(p)
