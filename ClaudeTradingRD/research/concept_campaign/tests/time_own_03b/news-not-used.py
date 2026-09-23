"""news-not-used (TTrades own voice, contested within the unit). Declared before any run.

Baseline (both readings): phase-3 bare 1h CISD, 2R, 10h hold (as news-events-ignored).

Reading a (x4sRGuZIqWk 'I don't really use macroeconomics and major news events in my
  trading decisions'): ignore the calendar entirely. Operationally IDENTICAL to
  news-events-ignored reading a: gate = decision on a scheduled-release trading day
  (FOMC or NFP), claim '+' (release-day trades no worse). The reading predicts NULL;
  NEGATIVE refutes it. Same frame and settings -> same hypothesis key in the ledger.
Reading b (N3Ml-r0X30o, FOMC day): 'I don't trade post FOMC'. gate 'allowed' = NOT
  (decision on an FOMC trading day at/after the 14:00 NY statement, until the 18:00 roll);
  claim '+'. The companion 'downgrade the 9:30 drive' clause is an expectation, not a
  trade rule, and is not separately tested (at most two readings).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params, release_flags

TF = "1h"


def detect(m1):
    ev = cisd_book(m1, TF)
    on, before, after = release_flags(ev["decision_time"])
    ev["release_day"] = on
    _, _, post_fomc = release_flags(ev["decision_time"], kinds=("FOMC",))
    ev["allowed_no_post_fomc"] = ~post_fomc
    return ev


CAL = {"calendar": "FOMC scheduled statement days (14:00 NY) + NFP (08:30 NY), 2016-2026; CPI not included"}
CAL_SRC = {"calendar": "declared-before-run: FOMC dates from federalreserve.gov calendars (fetched 2026-09-23), NFP by BLS reference-week rule"}

if __name__ == "__main__":
    ev = cl.cache_frame("t03b_newsnotused_cisd1h_v1", lambda: detect(cl.load_m1()))
    print(len(ev), "release-day share", ev["release_day"].mean(), "post-FOMC share", (~ev["allowed_no_post_fomc"]).mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    p, s = base_params(TF)
    base_rule = "baseline: phase-3 bare 1h CISD (series_open, 2/2, max_wait 3), decide at confirming 1h close, enter next M1 open, stop at protected swing, 2R, 10h hold"
    for reading, col, rule, note in (
        ("a", "release_day", "gate = decision on a scheduled-release trading day (FOMC or NFP); complement = all other days",
         "Reading a asserts news is not used; claim '+' = release-day trades no worse. NULL is consistent with the reading, NEGATIVE refutes it. Same operationalisation as news-events-ignored reading a."),
        ("b", "allowed_no_post_fomc", "gate 'allowed' = NOT (decision on an FOMC trading day at/after 14:00 NY); blocked = post-FOMC decisions that day",
         "Reading b: never trade post-FOMC (window to the 18:00 NY roll, 'wait for the next day' per method_spec §6). 9:30-downgrade clause not tested."),
    ):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold="10h", claim="+")
        for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
            print(reading, k, res.get(k))
        op = {"rules": [base_rule, rule], "params": {**p, **CAL, "post_fomc_window": "14:00 NY to the 18:00 NY daily roll"}}
        src = {**s, **CAL_SRC, "post_fomc_window": "method_spec §6: 'Never trade after FOMC; wait for the next day' (fomc-nfp-cpi-only)"}
        out = cl.write_result("news-not-used", reading, res, operationalization=op,
                              params_source=src, script=__file__, probe=probe, notes=note)
        print(out)
