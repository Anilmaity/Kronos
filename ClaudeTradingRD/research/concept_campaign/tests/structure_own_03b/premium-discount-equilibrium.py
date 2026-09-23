"""premium-discount-equilibrium (TTrades, MlMsG7li9zY / sgAnVR6RSDg) — gate_test, 2 readings.

Claim: longs only at discount (below the range's 0.5), shorts only at premium. '+' = the
filtered trades beat the rest of the same book.

Operationalisation (declared before the first run):
  * range = the latest CONFIRMED 4H fractal (2/2) swing high and swing low (forex grid),
    re-anchored to the running extreme of closed 4H bars while a new extreme forms
    ("re-anchor range_high to the running high each bar"). EQ = midpoint, wick to wick.
    4H is the structure TF paired with a 15m entry (method spec §1.2).
  * baseline book = phase-3 rung-0 15m CISD (series_open, swing 2/2, max_wait 3), stop =
    protected swing, 2R, 150min time exit. All hours.
  * reading a (entry location): long with the confirming close < EQ, short with close > EQ.
  * reading b (structure-point variant: "higher low in discount, lower high in premium"):
    the CISD's protected swing (the higher low / lower high the trade continues from)
    sits below EQ for a long / above EQ for a short.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402

MAX_HOLD = "150min"


def detect(m1):
    ev, _ = C.cisd_book(m1, "15min")
    b4 = cl.build_bars(m1, "4h", grid4h="forex")
    rg = C.swing_range(b4, ev["decision_time"])
    ok = rg["range_high"].notna().to_numpy() & rg["range_low"].notna().to_numpy()
    ev, rg = ev[ok].reset_index(drop=True), rg[ok].reset_index(drop=True)
    eq = (rg["range_high"].to_numpy() + rg["range_low"].to_numpy()) / 2
    d, px, sp = ev["direction"].to_numpy(), ev["px"].to_numpy(), ev["stop_px"].to_numpy()
    ev["eq"] = eq
    ev["entry_ok"] = ((d == 1) & (px < eq)) | ((d == -1) & (px > eq))
    ev["swing_ok"] = ((d == 1) & (sp < eq)) | ((d == -1) & (sp > eq))
    return ev.drop(columns=["bar_pos"])


OP_COMMON = [
    "range = latest confirmed 4H (forex grid) 2/2 swing high and swing low, each re-anchored to the running extreme of closed 4H bars since it; EQ = midpoint (wicks)",
    "baseline: 15m rung-0 CISD (series_open, 2/2, max_wait 3), stop protected swing, 2R, 150min exit, all hours"]
PARAMS = {"range_tf": "4h", "grid4h": "forex", "swing": "2/2", "baseline_tf": "15min",
          "max_wait": 3, "rr": 2.0, "max_hold": MAX_HOLD, "anchor": "wick"}
SRC = {"range_tf": "method_spec: §1.2 pairing 4-hour structure / 15-minute entry",
       "grid4h": "phase3: forex grid for gold (carried as a knob)",
       "swing": "phase3: swing_points left=2 right=2",
       "baseline_tf": "phase3: primary stack entry TF",
       "max_wait": "phase3: locked CISD config max_wait=3",
       "rr": "phase3: locked 2R target",
       "max_hold": "phase3: 10 entry-TF bars",
       "anchor": "method_spec: §3.7 EQ fib drawn wick high to wick low"}

if __name__ == "__main__":
    ev = cl.cache_frame("pde_cisd15_4hrange", lambda: detect(cl.load_m1()))
    print(len(ev), ev.entry_ok.mean(), ev.swing_ok.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    for rd, col, rule in (
            ("a", "entry_ok", "gate a: long with confirming close below EQ / short above EQ"),
            ("b", "swing_ok", "gate b: the protected swing (higher low / lower high) below EQ for longs / above EQ for shorts")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=MAX_HOLD)
        print("reading", rd)
        C.show(res)
        p = cl.write_result(
            "premium-discount-equilibrium", rd, res,
            operationalization={"rules": OP_COMMON + [rule], "params": PARAMS},
            params_source=SRC, script=__file__, probe=probe,
            notes="Contested: a = entry price location, b = structure-point location (variants.definition). Range selection ('most prominent range') is discretionary in the corpus; the latest confirmed 4H swings are the declared stand-in.")
        print(p)
