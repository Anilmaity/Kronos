"""trading-window (TTrades own voice, specified): his execution window is ~08:00-10:30 ET;
after ~10:30 he stops initiating.  A filter -> gate_test on a baseline book.

Baseline: phase-3 bare 5m CISD book (5m is in the concept's ltf list and is the phase-3
powered-cell entry TF), every event of the day.  Gate: decision_time (= entry moment) in
[08:00, 10:30) New York (DST-aware).  claim '+': gated trades beat the rest of the day
(control-adjusted).  The 'morning spent ranging -> downgrade' clause is qualitative
(no range test or cut-off quantified) and is not part of this reading.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, cisd_book, base_params, base_src, base_rule, HOLD, show  # noqa: E402

TF = "5min"
WIN = ("08:00", "10:30")


def detect(m1):
    ev = cisd_book(m1, TF)
    ev["in_window"] = cl.in_window(ev["decision_time"], *WIN)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("to02a_tradingwindow_5m_0800_1030", lambda: detect(cl.load_m1()))
    print(len(ev), "events; gate rate", ev["in_window"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "in_window", mask_available_at="decision_time", max_hold=HOLD[TF])
    show(res)
    op = {"rules": [base_rule(TF),
                    "gate: decision time (entry at the next M1 open) inside [08:00, 10:30) New York, DST-aware",
                    "complement: every other baseline event of the day",
                    "'morning ranging -> downgrade' clause not operationalised (unquantified in the corpus)"],
          "params": {**base_params(TF), "window": "08:00-10:30 NY", "tz": "America/New_York"}}
    src = {**base_src(TF, "corpus: concept timeframes.ltf lists 15m/5m/3m/1m; 5m = phase3 powered-cell entry TF"),
           "window": "corpus: aqnY1yZvfYs/Qv6Ux_Z8VrA (trading-window.yaml) 'approximately 08:00 to 10:30 ET'; 'After roughly 10:30 ET, stop initiating'",
           "tz": "method_spec: §1.4 DST settled, America/New_York"}
    print(cl.write_result("trading-window", None, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe))
