"""valid-structure-flip (guest: AP, gjoRPszj-Qk) -> trade_test.

Reading (declared before the run):
  * Working TF 15m (listed LTF), fractal 2/2 swings = the 'valid' swings; the active
    swing is the most recent confirmed, still-unbroken one.
  * Flip = a 15m CLOSE beyond the last valid swing against the direction of the
    previous break ('the last valid low we closed above, that's our market structure
    shift').  The first break of the data (no prior state) is never scored.
  * Strong low (bull) = the lowest low from the broken swing bar through the flip bar;
    'expect no return to it while the flip stands'.  Bias toward the weak high.
  * Trade: decide at the flip bar's close (harness enters next M1 open), in the flip
    direction; stop = the strong extreme (execution: 'stop beyond the strong extreme');
    target = 2R (the weak high sits at/near the flip close, so a structural target
    would be a near-zero distance; 2R is the phase-3 R target used for comparison).
  * max_hold 10h.  Rows whose stop is not on the losing side of the flip close dropped.
The GB-level entry (execution.entry) is tested separately under gb-retracement-entry.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_guest_01b")
from common01b import cl, bars_arr, structure_breaks, to_utc  # noqa: E402

TF = "15min"
SWING = (2, 2)
RR = 2.0
MAX_HOLD = "10h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bars_arr(cl.build_bars(m1, TF))
    br = structure_breaks(b, *SWING)
    br = br[br["count"] == 1]
    close = b["c"][br["bar"].to_numpy()]
    ok = (br["dir"].to_numpy() * (close - br["anchor"].to_numpy())) > 0
    br = br[ok]
    dt = to_utc(br["t"].to_numpy())
    return pd.DataFrame({"decision_time": dt, "available_at": dt,
                         "direction": br["dir"].to_numpy().astype(int),
                         "stop_px": br["anchor"].to_numpy(), "rr": RR}).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"vsf_{TF}_{SWING}_{RR}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "ties", "ctrl_overlap", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "15m bars; fractal 2/2 swings; active swing = most recent confirmed unbroken swing.",
        "Flip = 15m close beyond the active swing against the previous break's direction (first break of the data never scored).",
        "Strong extreme = lowest low (bull) / highest high (bear) from the broken swing bar through the flip bar.",
        "Decide at the flip bar close, trade in the flip direction; stop at the strong extreme; target 2R; max_hold 10h."],
        "params": {"tf": TF, "swing_left_right": SWING, "rr": RR, "max_hold": MAX_HOLD}}
    ps = {"tf": "declared-before-run: 15m (listed LTF; same as the sibling AP concepts)",
          "swing_left_right": "declared-before-run: fractal 2/2 = 'valid' swing (corpus gives no degree)",
          "rr": "phase3: 2R target of the locked conjunction book",
          "max_hold": "declared-before-run: 10h"}
    notes = ("Tests the claim that a close beyond the last valid swing sets the direction and the strong "
             "extreme holds (stop there) against a matched random entry with the same stop/target distance.")
    print(cl.write_result("valid-structure-flip", None, res, operationalization=op, params_source=ps,
                          script=__file__, probe=probe, notes=notes))
