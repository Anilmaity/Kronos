"""silver-bullet-window (TTrades own voice): the AM Silver Bullet window is 10:00-11:00 New
York; 'the only time he will take an entry is if the setup appears between 10 and 11', and
an order unfilled at 11:00 is cancelled.  A time filter -> gate_test.

The concept is contested only on whether OTHER windows exist (a PM version is mentioned
without a window) -- the one stated window has a single reading.
Baseline: phase-3 bare 5m CISD book (5m: nearest phase-3 entry TF to the concept's 1m ltf).
Gate: decision_time in [10:00, 11:00) NY, so the entry (next M1 open) fills no later than
10:55 and never after 11:00 (the cancel rule is satisfied by construction).
claim '+': in-window trades beat the rest of the day's book (control-adjusted).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, cisd_book, base_params, base_src, base_rule, HOLD, show  # noqa: E402

TF = "5min"
WIN = ("10:00", "11:00")


def detect(m1):
    ev = cisd_book(m1, TF)
    ev["in_sb"] = cl.in_window(ev["decision_time"], *WIN)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("to02a_silverbullet_5m_1000_1100", lambda: detect(cl.load_m1()))
    print(len(ev), "events; gate rate", ev["in_sb"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "in_sb", mask_available_at="decision_time", max_hold=HOLD[TF])
    show(res)
    op = {"rules": [base_rule(TF),
                    "gate: decision time inside [10:00, 11:00) New York (DST-aware); entry = next M1 open, so every gated fill is inside the window (unfilled-at-11:00 cancel satisfied by construction)",
                    "complement: every other baseline event of the day",
                    "the draw-on-liquidity precondition is not modelled (the concept gives no entry/stop/target; it is the window rule only)"],
          "params": {**base_params(TF), "window": "10:00-11:00 NY", "tz": "America/New_York"}}
    src = {**base_src(TF, "declared-before-run: concept ltf is 1m; 5m is the phase-3 powered-cell entry TF, nearest locked book"),
           "window": "corpus: o0v4KQxZbpU 'these entries have to fall within 10 to 11: a.m. window'",
           "tz": "method_spec: §1.4 DST settled, America/New_York"}
    print(cl.write_result("silver-bullet-window", None, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe))
