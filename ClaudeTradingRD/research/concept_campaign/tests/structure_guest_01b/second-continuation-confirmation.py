"""second-continuation-confirmation (guest: AP, gjoRPszj-Qk) -> gate_test.

Reading (declared before the run):
  * Same 15m / fractal 2/2 structure as valid-structure-flip.  Break = close beyond the
    active (most recent confirmed, unbroken) swing.  count 1 = the flip (first break
    against the previous direction); count 2 = the next same-direction break after it,
    i.e. 'the second new high established in the new direction'.  A break in the
    opposite direction resets the count (it is a new flip).
  * Baseline book = every count-1 and count-2 break, traded identically: decide at the
    breaking bar's close, direction of the break, stop at that break's strong extreme
    (lowest low from the broken swing bar through the breaking bar, mirrored), 2R target,
    max_hold 10h.
  * Gate is_second = count == 2.  Claim '+': the second continuation break is the
    better trade than the first flip.  cluster = the flip that opened the run.
  * The HTF-key-area conditioning is deliberately left open by the speaker (the YAML is
    'underspecified' for it); only the unconditional rule is tested.
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
    br = br[br["count"].isin([1, 2])]
    close = b["c"][br["bar"].to_numpy()]
    ok = (br["dir"].to_numpy() * (close - br["anchor"].to_numpy())) > 0
    br = br[ok]
    dt = to_utc(br["t"].to_numpy())
    return pd.DataFrame({"decision_time": dt, "available_at": dt,
                         "direction": br["dir"].to_numpy().astype(int),
                         "stop_px": br["anchor"].to_numpy(), "rr": RR,
                         "is_second": (br["count"].to_numpy() == 2),
                         "flip_id": br["flip_t"].to_numpy().astype("int64")}).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"scc_{TF}_{SWING}_{RR}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.is_second.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "is_second", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       cluster="flip_id")
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "ctrl_overlap", "exposure_bars", "control"):
        print(k, res.get(k))
    op = {"rules": [
        "15m bars; fractal 2/2 swings; break = close beyond the most recent confirmed unbroken swing.",
        "count 1 = flip (against the previous break); count 2 = next same-direction break (second continuation); opposite break resets.",
        "Book = count-1 and count-2 breaks: decide at the bar close, direction of break, stop at the strong extreme (broken swing bar..breaking bar), 2R, max_hold 10h.",
        "Gate is_second = count 2; complement = the first flip; cluster = the flip opening the run.",
        "HTF key-area conditioning not tested (speaker leaves it open)."],
        "params": {"tf": TF, "swing_left_right": SWING, "rr": RR, "max_hold": MAX_HOLD}}
    ps = {"tf": "declared-before-run: 15m (listed LTF; same as the sibling AP concepts)",
          "swing_left_right": "declared-before-run: fractal 2/2 = 'valid' swing (corpus gives no degree)",
          "rr": "phase3: 2R target of the locked conjunction book",
          "max_hold": "declared-before-run: 10h"}
    notes = ("Mask known at the breaking bar's close (the count is computed from past breaks only). "
             "HTF key-area split (the concept's stated conditioning) is not decidable without importing a POI definition the speaker declines to give.")
    print(cl.write_result("second-continuation-confirmation", None, res, operationalization=op,
                          params_source=ps, script=__file__, probe=probe, notes=notes))
