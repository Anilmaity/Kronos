"""killzones (TTrades own voice + guests, contested) — gate_test, two readings.

Claim: high-probability moves occur during kill zones; "a setup that triggers outside a
killzone is not taken" (OTE video, MPeeE55rNOw). Two distinct readings (declared before any
run), each a clock gate on the batch baseline book (5m bare CISD, _common.py):

  a  The taught kill-zone grid as a filter. Gold is a forex-class instrument (the corpus
     itself says the NY windows differ for forex vs indices, and the forex 4H grid is the
     one locked for gold), so the FOREX grid is used: Asia 20:00-00:00, London 02:00-05:00,
     New York AM 07:00-10:00, London Close 10:00-12:00 NY. Gate = entry time inside any
     of them; complement = outside every kill zone.
  b  His own earlier-recordings choice (A8UpRZlRzlg "I trade the New York open"; the only
     explicit clock reading of that unit, CAuN4tvLInQ "8 30 start and then we get into
     9 30"): gate = entry time inside [08:30, 09:30) NY; complement = the rest of the day.
     His 1m/15s execution is not modelled (5m baseline).

The guest windows (Trader T, Ben, $niper) are other traders' clocks and are not this
concept's own-voice claim; they are not tested here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "killzones"
FX = [cl.KILLZONES[k] for k in ("fx_asia", "fx_london", "fx_ny_am", "fx_london_close")]
READINGS = {
    "a": {"window": FX,
          "src": "session_window_fit: forex kill-zone grid, killzones.yaml verbatim-verified "
                 "against MPeeE55rNOw (Asia 20-00, London 02-05, NY AM 07-10, London Close "
                 "10-12); forex grid because gold is forex-class",
          "desc": "entry time inside any forex kill zone (Asia 20-00, London 02-05, NY AM "
                  "07-10, London Close 10-12 NY); complement = outside all kill zones"},
    "b": {"window": [("08:30", "09:30")],
          "src": "corpus: CAuN4tvLInQ 'which is right about here 8 30 start and then we get "
                 "into 9 30'; A8UpRZlRzlg 'I trade the New York open'",
          "desc": "entry time inside the New York open 08:30-09:30 NY; complement = rest of day"},
}


def make_detect(window):
    def detect(m1):
        ev = C.cisd5(m1)
        ev["in_kz"] = C.window_mask(ev["decision_time"], window)
        return ev
    return detect


if __name__ == "__main__":
    base = C.base_cached()
    for rd, spec in READINGS.items():
        detect = make_detect(spec["window"])
        ev = base.copy()
        ev["in_kz"] = C.window_mask(ev["decision_time"], spec["window"])
        probe = cl.probe_lookahead(detect, ev, lookback="10D")
        res = cl.gate_test(ev, "in_kz", mask_available_at="decision_time",
                           max_hold=C.BASE_MAX_HOLD, claim="+")
        op = {"rules": [
            "baseline: 5m bare CISD (series_open, 2/2 swings, max_wait 3), decide at the "
            "confirming 5m close, enter next M1 open, stop = protected swing, 2R, 50 min exit",
            "gate: " + spec["desc"] + " (America/New_York, DST-aware)"],
            "params": dict(C.BASE_PARAMS, window=spec["window"], tz="America/New_York")}
        src = dict(C.BASE_SRC, window=spec["src"],
                   tz="session_window_fit: America/New_York with DST (settled)")
        notes = ("Kill zone as an entry filter on a whole-day 5m CISD book. Guest windows "
                 "(Trader T server clock, Ben PM, $niper AM) not tested: other traders' "
                 "clocks, Trader T's on an unstated broker offset.")
        p = cl.write_result(CID, rd, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe, notes=notes)
        print(rd, p)
        for k in ("n", "verdict", "verdict_detail", "diff", "ci_lo", "ci_hi", "p", "mde",
                  "ties", "halves"):
            print("  ", k, res.get(k))
