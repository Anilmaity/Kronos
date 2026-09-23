"""entry-time-window (TTrades own voice, contested) — gate_test, two readings.

The concept is a timing filter: take entries only inside his New York morning window.
Status contested; the corpus gives several windows. Two distinct readings are tested
(declared before any run), each as a clock gate on the batch baseline book (5m bare CISD,
phase-3 locked config, 2R, 50 min — see _common.py):

  a  "Trade only 08:30 to 11:00" — the variant name; 0bH_kkG2q6s: asked "do I only trade
     between 8:30 and 11" the host answers yes. Gate: entry (decision) time in
     [08:30, 11:00) New York.
  b  "The opening drive 9:30 to 10:00" — the primary definition; G1IIdQ3RAkY "normally I
     want this move to occur from 9:30 to 10". Gate: entry time in [09:30, 10:00) NY.

Claim '+': entries inside the window beat entries outside it (control-adjusted).
Clock: America/New_York with DST (settled, session_window_fit §5).
The kill-zone rejection / "HTF candle has formed its wick" part is not modelled here
("formed a wick" is unquantified in the concept); it is covered by other concepts.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "entry-time-window"
READINGS = {
    "a": {"window": [("08:30", "11:00")],
          "src": "corpus: 0bH_kkG2q6s 'do i only trade between 8 30 and 11 and the answer' / "
                 "'the answer for me is yes that's just what works with my schedule'"},
    "b": {"window": [("09:30", "10:00")],
          "src": "corpus: G1IIdQ3RAkY 'normally I want this move to occur from 9:30 to 10'"},
}


def make_detect(window):
    def detect(m1):
        ev = C.cisd5(m1)
        ev["in_window"] = C.window_mask(ev["decision_time"], window)
        return ev
    return detect


if __name__ == "__main__":
    base = C.base_cached()
    for rd, spec in READINGS.items():
        detect = make_detect(spec["window"])
        ev = base.copy()
        ev["in_window"] = C.window_mask(ev["decision_time"], spec["window"])
        probe = cl.probe_lookahead(detect, ev, lookback="10D")
        res = cl.gate_test(ev, "in_window", mask_available_at="decision_time",
                           max_hold=C.BASE_MAX_HOLD, claim="+")
        op = {"rules": [
            "baseline: 5m bare CISD (series_open, 2/2 swings, max_wait 3), decide at the "
            "confirming 5m close, enter next M1 open, stop = protected swing, 2R, 50 min exit",
            f"gate: entry time inside {spec['window']} New York (DST-aware); complement = "
            "every other baseline entry of the day"],
            "params": dict(C.BASE_PARAMS, window=spec["window"], tz="America/New_York")}
        src = dict(C.BASE_SRC, window=spec["src"],
                   tz="session_window_fit: America/New_York with DST (settled, 99.8% of 605 "
                      "daily breaks resume at 18:00 NY)")
        notes = ("Gate on the whole-day 5m CISD book; the kill-zone-rejection / 'HTF candle "
                 "already formed its wick' rider is not modelled (unquantified).")
        p = cl.write_result(CID, rd, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe, notes=notes)
        print(rd, p)
        for k in ("n", "verdict", "verdict_detail", "diff", "ci_lo", "ci_hi", "p", "mde",
                  "ties", "halves"):
            print("  ", k, res.get(k))
