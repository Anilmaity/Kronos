"""new-york-only-930-1130-window (guest: NickDoesFutures) -> gate_test.

Claim ('+'): trades taken only in 09:30-11:30 New York beat trades taken outside it.
Declared before the run:
  * Time zone: America/New_York with DST (the guest states none; the settled project
    convention, and 09:30 is the NY cash open he trades around).
  * Window: entry-only (decision_time in [09:30, 11:30) NY). The ambiguity "does it also
    force an exit at 11:30" is inert here: the baseline book's hold is 50 min, so the
    latest in-window trade ends by 12:20.
  * Baseline book: phase-3 bare 5m CISD (series_open, swing 2/2, max_wait 3, stop at the
    protected swing, 2R, 10 bars = 50 min) — 5m is in the concept's ltf list and is the
    generic intraday execution model of this corpus; the guest's own entry model
    (unicorn) is tested under its own concept.
  * Gate column in_window emitted by the detector; complement = every other clock time.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_guest_01c")
from _common import PHASE3, cisd_book, cl, summary  # noqa: E402

CID = "new-york-only-930-1130-window"
TF, HOLD = "5min", "50min"
WIN = ("09:30", "11:30")


def detect(m1):
    ev = cisd_book(m1, TF)
    ev["in_window"] = cl.in_window(ev["decision_time"], *WIN).astype(bool)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("tg01c_cisd5m_ny0930_1130", lambda: detect(cl.load_m1()))
    print(len(ev), ev["in_window"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "in_window", mask_available_at="decision_time", max_hold=HOLD)
    print(summary(res))
    op = {"rules": [
        "baseline: 5m bare CISD (series_open, swing 2/2, max_wait 3), decide at the confirming "
        "bar close, enter next M1 open, stop at the protected swing, 2R, 50 min hold",
        "gate: decision time in [09:30, 11:30) America/New_York (DST-aware); complement = "
        "all other times; entry-only window (hold 50 min makes a forced 11:30 exit inert)"],
        "params": {"window": "09:30-11:30", "tz": "America/New_York", "tf": TF,
                   "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": 2.0,
                   "max_hold": HOLD, "grid4h": "n/a (5m)"}}
    src = {"window": "corpus: tDiwwMRWF2k 'I just trade from 9:30 to 11:30'",
           "tz": "session_window_fit: America/New_York with DST (settled)",
           "tf": "declared-before-run: 5m, in the concept's ltf list; phase-3 bare CISD as the baseline book",
           "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Guest trades index futures; the NY clock window is applied to "
                              "XAUUSD as stated. Only the timing rule is tested, on a generic "
                              "5m CISD baseline book.")
    print(p)
