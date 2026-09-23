"""strat-candle-taxonomy (guest: Alex's Options, 1XWyy6Q-_8Q) -> trade_test.

The 1/2/3 taxonomy itself is definitional (every candle is exactly one type) and cannot
be false.  Its one predictive assertion is 'when we see a 2 we know that is trending':
a 2 is directional.  Reading (declared before the run):
  * 1h bars (listed LTF), types vs the previous bar; equal high/low does NOT count as
    taken (the corpus leaves equality open; strict inequality is the literal 'took').
  * Every closed 2-up -> long at its close (harness: next M1 open); 2-down -> short.
  * Stop = the 2's own opposite extreme (its low for a 2-up), target 1R (a symmetric
    bracket: pure direction), max_hold 10h.
  * Measured against the harness's matched random entry (same direction, stop and target
    distance, +/-30d), so 'trending' must mean better than a coin-flip bracket.
The 'a 3 fails near the beginning of the candle' tendency is not scored: it is stated as a
tendency with no threshold and has no geometry-matched null that isolates it from the
generic early-extreme timing of any bar.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_guest_01b")
from common01b import cl, bars_arr, strat_types, to_utc  # noqa: E402

TF = "1h"
RR = 1.0
MAX_HOLD = "10h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bars_arr(cl.build_bars(m1, TF))
    h, l, c = b["h"], b["l"], b["c"]
    t = strat_types(h, l)
    up = np.flatnonzero(t == 2)
    dn = np.flatnonzero(t == -2)
    f = pd.DataFrame({"bar": np.r_[up, dn],
                      "direction": np.r_[np.ones(len(up), int), -np.ones(len(dn), int)]})
    f["stop_px"] = np.where(f["direction"] == 1, l[f["bar"]], h[f["bar"]])
    d = f["direction"].to_numpy()
    f = f[d * (c[f["bar"].to_numpy()] - f["stop_px"].to_numpy()) > 0].copy()
    f["decision_time"] = to_utc(b["close_t"][f["bar"].to_numpy()])
    f["available_at"] = f["decision_time"]
    f["rr"] = RR
    f = f.sort_values("decision_time", kind="stable").reset_index(drop=True)
    return f[["decision_time", "available_at", "direction", "stop_px", "rr"]]


if __name__ == "__main__":
    ev = cl.cache_frame(f"strat_tax_{TF}_{RR}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "ties", "ctrl_overlap", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "1h bars; 2-up = high > prev high and low >= prev low; 2-down mirrored (strict inequalities).",
        "Trade every closed 2 in its direction at its close; stop at the 2's opposite extreme; 1R target; max_hold 10h.",
        "Claim '+': a 2 is trending (beats the matched random bracket)."],
        "params": {"tf": TF, "rr": RR, "max_hold": MAX_HOLD, "equal_extreme_taken": False}}
    ps = {"tf": "declared-before-run: 1h (listed LTF)",
          "rr": "declared-before-run: 1R symmetric bracket isolates direction",
          "max_hold": "declared-before-run: 10h (10 bars)",
          "equal_extreme_taken": "corpus: 1XWyy6Q-_8Q 'any candle that takes previous high or low' (strict 'takes'; equality unaddressed)"}
    notes = ("Taxonomy is definitional; only the '2 is trending' assertion is scored. The 3-fails-early "
             "tendency is left unscored (no threshold, no isolating null).")
    print(cl.write_result("strat-candle-taxonomy", None, res, operationalization=op, params_source=ps,
                          script=__file__, probe=probe, notes=notes))
