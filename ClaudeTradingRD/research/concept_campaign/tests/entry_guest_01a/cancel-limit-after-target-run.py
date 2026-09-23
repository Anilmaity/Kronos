"""cancel-limit-after-target-run — Trader T: if a pending limit has not filled and price
runs to the take-profit first, delete it (fills after a target-run mostly stop out).

gate_test on Trader T's own book (htf-reaction-mss-retrace-entry reading a) WITHOUT the
cancel rule: 1h swing sweep -> 5m close through the pre-sweep relative fractal ->
limit at the latest 5m FVG of the shift -> stop = sweep extreme, 2R.  Gate `kept` =
the limit filled BEFORE the 2R price had traded (the orders the rule keeps);
complement = fills that came after price had already reached the target (the orders
the rule cancels).  claim '+': kept fills do better (control-adjusted).
"""
import sys

import numpy as np

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a")
from common01a import cl, trader_t_setups  # noqa: E402

HNS = np.int64(3600 * 10 ** 9)
A = dict(htf="1h", ltf="5min", swing=(2, 2), sweep_window_ns=120 * HNS, bos_bars=72, expiry_ns=12 * HNS, rr=2.0)
HOLD = "12h"


def detect(m1):
    ev = trader_t_setups(m1, **A)
    ev["kept"] = ~ev["ran_first"].astype(bool)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("cancel_limit_traderT_1h5m_v1", lambda: detect(cl.load_m1()))
    print(len(ev), "kept share", ev.kept.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "kept", mask_available_at="decision_time", max_hold=HOLD, ctrl_tod_tol_min=30)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "Baseline = Trader T book as htf-reaction-mss-retrace-entry reading a, but with NO cancel: every limit that fills within 12h is traded.",
        "ran_first = the 2R target price traded on an M1 bar strictly before the fill bar (order of events, not elapsed time).",
        "Gate kept = not ran_first (known at the fill = decision time). Stop = sweep extreme, target 2R, max hold 12h."],
        "params": {**{k: (str(v) if isinstance(v, np.integer) else v) for k, v in A.items()},
                   "sweep_window": "5D", "expiry": "12h", "max_hold": HOLD, "ctrl_tod_tol_min": 30}}
    ps = {"rr": "corpus: wCtxmWe4KNc 'I just took a simple 2R' (the fixed target the rule references)",
          "cancel_rule": "corpus: wCtxmWe4KNc 'when it runs to my TV before filling my order in most cases it will go through my stop loss'",
          "htf": "corpus: wCtxmWe4KNc hourly sweep", "ltf": "corpus: wCtxmWe4KNc 'break and structure on the five minutes'",
          "swing": "declared-before-run: fractal 2/2",
          "sweep_window_ns": "declared-before-run: 5 days", "sweep_window": "declared-before-run: 5 days",
          "bos_bars": "declared-before-run: 72 5m bars (6h)",
          "expiry_ns": "declared-before-run: 12h", "expiry": "declared-before-run: 12h",
          "max_hold": "declared-before-run: 12h", "ctrl_tod_tol_min": "declared-before-run: 30 (README trap 9)"}
    print(cl.write_result("cancel-limit-after-target-run", None, res, operationalization=op, params_source=ps,
                          script=__file__, probe=probe))
