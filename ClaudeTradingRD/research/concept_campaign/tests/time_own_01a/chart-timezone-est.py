"""chart-timezone-est (TTrades own voice, specified) — gate_test.

The concept: his model indicator runs on EST, and its session filter hides every printed
setup outside the chosen session (New York is the example: "not wanting to see setups that
occur while you are asleep"). sdZkE-naNiY gives no numeric bounds for the New York
filter; the same indicator's setup time filter is stated numerically, with timezone, in
Je7cd9HJUBE: "I only want to see setups between 8 to 11 EST". That is the only numeric
setting of this filter in the corpus, so it is the gate tested here (declared before any
run). The clock-identity half of the concept ("times are EST") is a chart convention; its
decidable consequence is tested under est-timezone-anchor, and the DST question is settled
(America/New_York, session_window_fit).

Baseline: the batch 5m bare CISD book (_common.py) — the fractal-model indicator prints
CISD-confirmed setups on the LTF. Gate: entry time inside [08:00, 11:00) New York.
Claim '+': setups the filter keeps beat the ones it hides.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "chart-timezone-est"
WINDOW = [("08:00", "11:00")]


def detect(m1):
    ev = C.cisd5(m1)
    ev["session_filter"] = C.window_mask(ev["decision_time"], WINDOW)
    return ev


if __name__ == "__main__":
    ev = C.base_cached().copy()
    ev["session_filter"] = C.window_mask(ev["decision_time"], WINDOW)
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "session_filter", mask_available_at="decision_time",
                       max_hold=C.BASE_MAX_HOLD, claim="+")
    op = {"rules": [
        "baseline: 5m bare CISD (series_open, 2/2 swings, max_wait 3), decide at the "
        "confirming 5m close, enter next M1 open, stop = protected swing, 2R, 50 min exit",
        "session filter ON = entry time inside 08:00-11:00 New York (EST read as the "
        "DST-aware New York clock); complement = the setups the filter hides"],
        "params": dict(C.BASE_PARAMS, window=WINDOW, tz="America/New_York")}
    src = dict(C.BASE_SRC,
               window="corpus: Je7cd9HJUBE 'I only want to see setups between 8 to 11 EST' "
                      "(same indicator's setup time filter; sdZkE-naNiY gives no bounds)",
               tz="session_window_fit: America/New_York with DST (settled)")
    notes = ("The concept's own video gives the New York filter without bounds; the numeric "
             "setting 08:00-11:00 EST comes from the same indicator in Je7cd9HJUBE. "
             "Timezone identity itself is a convention, tested via est-timezone-anchor.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "verdict", "verdict_detail", "diff", "ci_lo", "ci_hi", "p", "mde",
              "ties", "halves"):
        print("  ", k, res.get(k))
