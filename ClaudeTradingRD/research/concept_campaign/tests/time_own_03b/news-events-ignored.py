"""news-events-ignored (TTrades own voice, contested). Two readings, declared before any run.

Baseline book (both readings): phase-3 bare 1h CISD (daily-bias TF 1D is the concept's only
timeframe; the 1h book is the phase-3 locked intraday baseline), 2R, 10h hold.
Release calendar: scheduled FOMC statement days (14:00 NY) + NFP days (08:30 NY), see
_common.py; 'release day' = the NY trading day (18:00 roll) containing the release.

Reading a (stated policy, 'Nothing changes for me', 'news lately ... doesn't care'):
  the model is unchanged by a scheduled release, i.e. release-day trades are no worse than
  other trades. gate = decision on a release day; claim '+'. The reading predicts NULL
  (no difference); NEGATIVE (release-day trades worse) refutes it.
Reading b (observed behaviour, 'I was waiting for NFP'): a pending release is a reason to
  wait. gate 'allowed' = NOT (decision on a release day before the release); claim '+'
  (waiting improves the book).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params, release_flags

TF = "1h"


def detect(m1):
    ev = cisd_book(m1, TF)
    on, before, after = release_flags(ev["decision_time"])
    ev["release_day"] = on
    ev["allowed_wait"] = ~before
    return ev


CAL = {"calendar": "FOMC scheduled statement days (14:00 NY) + NFP (08:30 NY), 2016-2026; CPI not included"}
CAL_SRC = {"calendar": "declared-before-run: FOMC dates from federalreserve.gov calendars (fetched 2026-09-23), NFP by BLS reference-week rule; corpus names CPI/NFP/FOMC (X4XSsv5CNqg)"}

if __name__ == "__main__":
    ev = cl.cache_frame("t03b_news_cisd1h_v1", lambda: detect(cl.load_m1()))
    print(len(ev), "release-day share", ev["release_day"].mean(), "blocked share", (~ev["allowed_wait"]).mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    p, s = base_params(TF)
    base_rule = "baseline: phase-3 bare 1h CISD (series_open, 2/2, max_wait 3), decide at confirming 1h close, enter next M1 open, stop at protected swing, 2R, 10h hold"
    for reading, col, rule, note in (
        ("a", "release_day", "gate = decision on a scheduled-release trading day (FOMC or NFP); complement = all other days",
         "Reading a asserts NO change on release days; the claim is set '+' (release-day trades no worse). NULL is consistent with the reading, NEGATIVE refutes it."),
        ("b", "allowed_wait", "gate 'allowed' = NOT (decision on a release trading day before the release time); blocked = pre-release decisions on release days",
         "Reading b: waiting for the release; claim '+' = the filter improves the book."),
    ):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold="10h", claim="+")
        for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
            print(reading, k, res.get(k))
        op = {"rules": [base_rule, rule], "params": {**p, **CAL}}
        out = cl.write_result("news-events-ignored", reading, res, operationalization=op,
                              params_source={**s, **CAL_SRC}, script=__file__, probe=probe,
                              notes=note + " CPI days are not flagged (no verifiable calendar), which can only attenuate.")
        print(out)
