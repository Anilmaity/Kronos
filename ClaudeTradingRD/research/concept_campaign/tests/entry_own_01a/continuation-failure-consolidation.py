"""continuation-failure-consolidation — a SLOW (non-V) closure through the level is a consolidation sweep.

Concept: concepts/entry/continuation-failure-consolidation.yaml. Rules: "Test the recovery: does price
close back over the level? A slow, non-V-shaped return means no." / "Measure the recovery speed into the
level (see v-shape-reversal-speed: 1-3 candles)" / "This closure through which you think is validating
this low is actually a manipulation" -> reclassifying "saves you from a loss".

Test (one reading): gate_test. Baseline = every 15m CISD closure (series_open, 2/2 swing, POI on,
protected-swing stop, 2R, 150min) with the closure allowed up to 40 bars late (phase-3 declared
secondary max_wait=40, 'effectively unbounded'). Gate `fast` = the closure arrived within 3 bars of
the swing becoming confirmable (the phase-3 max_wait=3 speed rule, "1, 2, maybe three"); the
complement are the slow closures he reclassifies as consolidation sweeps. claim '+': fast beats slow.
Route A / Route B re-entries are not separately tested (the concept is carried by the speed test that
decides whether the closure is traded at all).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np           # noqa: E402

import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402

TF = "15min"
MAX_HOLD = "150min"
RR = 2.0
MAX_WAIT_ALL = 40
FAST = 3


def detect(m1):
    b, ev = C.cisd_with_poi(m1, TF, level_rule="series_open", max_wait=MAX_WAIT_ALL, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "wait_bars", "fast"]
    if ev.empty:
        return C.empty_frame(cols)
    ev = ev[ev["poi_passed"]].reset_index(drop=True)
    if ev.empty:
        return C.empty_frame(cols)
    send = b.index.get_indexer(ev["series_end"])
    begin = np.maximum(send, ev["ext_pos"].to_numpy() + 2) + 1
    out = C.to_trade_frame(ev, RR)
    out["wait_bars"] = (ev["conf_pos"].to_numpy() - begin).astype(float)
    out["fast"] = out["wait_bars"].to_numpy() < FAST
    return out


PARAMS_SOURCE = {
    "baseline": "phase3: §1.8 CISD (15m, series_open, 2/2, min_series 1) with POI gate on, "
                "protected-swing stop, 2R (§1.12), 10-bar hold (§1.13)",
    "max_wait_all": "phase3: §1.8 declared secondary max_wait=40 (effectively unbounded)",
    "fast": "phase3: §1.8 max_wait=3 — corpus 'I prefer 1, 2, maybe three' "
            "(v-shape-reversal-speed, cited by this concept's own rule 8)",
    "max_hold": "phase3: §1.13 10 entry-TF bars",
    "tf": "method_spec: §1.3 favourite stack 4H/15m; concept ltf lists 15m",
}


if __name__ == "__main__":
    ev = cl.cache_frame(f"eo01a_cfc_{TF}_mw{MAX_WAIT_ALL}_fast{FAST}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "fast share", ev["fast"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="12D")
    res = cl.gate_test(ev, "fast", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "baseline: 15m CISD closures (series_open, 2/2, min_series 1, max_wait 40) with POI gate "
        "on; decide at confirm close; stop protected swing; 2R; 150min",
        "gate fast: closure within 3 bars after the swing is confirmable (wait_bars < 3); "
        "complement = slow closure = consolidation sweep per the concept"],
        "params": {"tf": TF, "baseline": "cisd_mw40_poi", "max_wait_all": MAX_WAIT_ALL,
                   "fast": FAST, "max_hold": MAX_HOLD}}
    p = cl.write_result("continuation-failure-consolidation", None, res, operationalization=op,
                        params_source=PARAMS_SOURCE, script=__file__, probe=probe)
    print("wrote", p)
