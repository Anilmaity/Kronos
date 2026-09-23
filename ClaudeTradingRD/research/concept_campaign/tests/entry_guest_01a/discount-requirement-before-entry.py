"""discount-requirement-before-entry — no short unless the entry is above equilibrium
(premium), no long unless below (discount).  Contested on WHICH range: two readings,
both gate_test on the $niper book (htf-reaction-mss-retrace-entry reading b: previous-day
high/low taken -> 15m MSS with FVG -> limit at the FVG, stop = sweep extreme, target =
opposing previous-day extreme; missed if the target trades first).

(a) $niper: range = the leg that produced the MSS (sweep extreme -> leg extreme through
    the last M1 bar before the fill); gate = limit price in the correct half.
(b) variant (Gene / 'a range with a defined high and low'): range = the current trading
    day's range so far (18:00 NY open -> last M1 bar before the fill).
"""
import sys

import numpy as np

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a")
from common01a import cl, niper_pdhl_setups  # noqa: E402

HNS = np.int64(3600 * 10 ** 9)
B = dict(ltf="15min", swing=(2, 2), mss_bars=24, expiry_ns=12 * HNS)
HOLD = "24h"


def detect(m1):
    return niper_pdhl_setups(m1, **B)


if __name__ == "__main__":
    ev = cl.cache_frame("discount_niper_pdhl_15m_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev[["prem_leg", "prem_day"]].mean().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    base_rules = [
        "Baseline = $niper book exactly as htf-reaction-mss-retrace-entry reading b (15m, prior-day high/low taken, MSS within 6h same day with FVG, limit at FVG near edge, stop sweep extreme, target opposite prior-day extreme, 12h expiry, missed if target first).",
        "Wick vs body: the LIMIT PRICE is what must sit in the correct half (the entry array's near edge)."]
    ps_base = {"ltf": "corpus: UmLWRlXd_V8 'drop to the 15-minute or the hourly' -> 15m",
               "swing": "declared-before-run: fractal 2/2",
               "mss_bars": "declared-before-run: 24 15m bars (6h), same trading day",
               "expiry_ns": "declared-before-run: 12h", "expiry": "declared-before-run: 12h",
               "max_hold": "declared-before-run: 24h",
               "ctrl_tod_tol_min": "declared-before-run: 30 (README trap 9)",
               "eq": "corpus: UmLWRlXd_V8 'I don't take a short unless price is above equilibrium' (50%)"}
    params = {**{k: (str(v) if isinstance(v, np.integer) else v) for k, v in B.items()},
              "expiry": "12h", "max_hold": HOLD, "ctrl_tod_tol_min": 30, "eq": 0.5}
    for reading, col, rule, src in (
            ("a", "prem_leg",
             "Gate prem_leg: fib from the sweep extreme to the MSS leg's opposite extreme (15m bars sweep..MSS plus M1 up to the bar before the fill); short limit above 50% / long limit below 50%.",
             "corpus: UmLWRlXd_V8 'The fib is drawn from the high to the low of the leg that produced the market structure break'"),
            ("b", "prem_day",
             "Gate prem_day: range = current trading day (18:00 NY roll) high/low from the open through the M1 bar before the fill; short limit above 50% / long limit below 50%.",
             "declared-before-run: variant 'A range with a defined high and low has been chosen' — range unspecified in the corpus; the day's running range chosen")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD, ctrl_tod_tol_min=30)
        print(reading, {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail")})
        op = {"rules": base_rules + [rule], "params": {**params, "range": col}}
        ps = {**ps_base, "range": src}
        print(cl.write_result("discount-requirement-before-entry", reading, res, operationalization=op,
                              params_source=ps, script=__file__, probe=probe))
