"""gb-levels — are AP's deep GB levels (0.705 / 0.7475 / 0.79) better limit entries than
the standard fib control set named in the concept's own `measurable` (0.5, 0.618, 0.786)?

gate_test. Baseline book = one resting limit per level per 15m structure flip (six
levels), same anchor, same stop (anchor extreme), same target (the 0.41 level), same
expiry.  Gate = the level is a GB level.  Control-adjusted R removes the geometry each
level's different stop/target distance implies; clusters = the flip.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a")
from common01a import cl, bars_arr, m1_arrays, structure_flips, gb_limit_fill, to_utc, NS_MIN  # noqa: E402

TF = "15min"
GB = (0.705, 0.7475, 0.79)
CTRL = (0.5, 0.618, 0.786)
X_TGT = 0.41
EXPIRY_NS = np.int64(24 * 3600 * 10 ** 9)
MAX_HOLD = "24h"
SWING = (2, 2)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bars_arr(cl.build_bars(m1, TF))
    m = m1_arrays(m1)
    fl = structure_flips(b, *SWING)
    rows = []
    for r in fl.itertuples(index=False):
        t_to = min(int(r.flip_t) + EXPIRY_NS, int(r.cancel_t))
        for x in sorted(GB + CTRL):
            f = gb_limit_fill(m, int(r.flip_t), t_to, int(r.dir), float(r.anchor), float(r.opp0), x)
            if f is None:
                continue
            k, lvl, opp, _ = f
            rng = abs(opp - r.anchor)
            rows.append((int(m["t"][k]) + NS_MIN, int(r.dir), (1 - x) * rng, (x - X_TGT) * rng,
                         x, x in GB, lvl, int(r.flip_t)))
    ev = pd.DataFrame(rows, columns=["dt", "direction", "stop_dist", "target_dist", "level",
                                     "is_gb", "limit_px", "flip_t"])
    ev.insert(0, "decision_time", to_utc(ev["dt"].to_numpy()))
    ev["available_at"] = ev["decision_time"]
    ev["flip_id"] = ev["flip_t"].astype("int64")
    ev["flip_t"] = to_utc(ev["flip_t"].to_numpy())
    return ev.drop(columns="dt").sort_values(["decision_time", "level"], kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"gb_levels_{TF}_{GB}_{CTRL}_{X_TGT}_24h_sw22", lambda: detect(cl.load_m1()))
    print(len(ev), ev.groupby("level").size().to_dict(), "gated share", ev.is_gb.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "is_gb", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       ctrl_tod_tol_min=30, cluster="flip_id")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "Same flips/anchor/running-extreme/limit mechanics as gb-retracement-entry (15m, fractal 2/2, flip = close beyond last confirmed unbroken swing against the previous break).",
        "One resting limit per level in {0.5, 0.618, 0.705, 0.7475, 0.786, 0.79}; each fills on the first M1 bar through it; decision = that bar's close.",
        "Every level: stop = anchor extreme (level 1.0), target = the 0.41 level; distances fixed at the limit price.",
        "Cancel at the next opposite flip or 24h after the flip.",
        "Gate is_gb = level in {0.705, 0.7475, 0.79}; complement = the standard control set {0.5, 0.618, 0.786}; cluster = flip."],
        "params": {"tf": TF, "gb_levels": GB, "control_levels": CTRL, "x_target": X_TGT, "expiry": "24h",
                   "max_hold": MAX_HOLD, "swing_left_right": SWING, "ctrl_tod_tol_min": 30}}
    ps = {"gb_levels": "corpus: gjoRPszj-Qk '0.705/0.7475/0.79 form the deep-retracement entry zone'",
          "control_levels": "corpus-derived: gb-levels.yaml measurable 'versus a control set of levels (0.5, 0.618, 0.786)'",
          "x_target": "corpus: gjoRPszj-Qk targets '0.41'",
          "tf": "declared-before-run: 15m (listed LTF)",
          "swing_left_right": "declared-before-run: fractal 2/2",
          "expiry": "declared-before-run: 24h or next opposite flip",
          "max_hold": "declared-before-run: 24h",
          "ctrl_tod_tol_min": "declared-before-run: 30 (README trap 9)"}
    notes = ("The 0.41/0.295 target claims are not scored here; 0.786 vs 0.79 are near-identical fills by "
             "construction, so the comparison is weighted to 0.705/0.7475 vs 0.5/0.618.")
    p = cl.write_result("gb-levels", None, res, operationalization=op, params_source=ps,
                        script=__file__, probe=probe, notes=notes)
    print(p)
