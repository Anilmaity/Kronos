"""cisd-skip-at-target — skip the CISD entry when the CISD closure leaves no room to the short-term target.

Concept: concepts/entry/cisd-skip-at-target.yaml. Rule: "Compare the CISD closure level to the distance
remaining to the short-term target. If the CISD level is at or beyond the target, do not use the CISD
entry." Measurable: "share of signals where the CISD level leaves less than 1R to the target".

Test: gate_test on the baseline book = the cisd reading-a book (15m, series_open, POI on, stop at the
protected swing, 2R, 150min). Gate `room_ok` = the entry closure leaves >= 1R to the short-term target
(the rule says skip otherwise), claim '+': the kept (room_ok) trades beat the skipped ones.

Short-term target (declared before run): the most recent CONFIRMED 15m 2/2 swing on the opposite side
before the extreme (bullish: the last swing high before the low = the short-term high the leg came
from), searched within the phase-3 POI range lookback of 40 bars; swings count only if confirmed
(p+2) at or before the confirming bar. Events with no such swing have no defined target and are
dropped from the book (the rule cannot be evaluated there).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

TF = "15min"
MAX_HOLD = "150min"
RR = 2.0
LOOKBACK = 40
MIN_ROOM_R = 1.0


def detect(m1):
    b, ev = C.cisd_with_poi(m1, TF, level_rule="series_open", max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "room_R", "room_ok"]
    if ev.empty:
        return C.empty_frame(cols)
    ev = ev[ev["poi_passed"]].reset_index(drop=True)
    if ev.empty:
        return C.empty_frame(cols)
    sw = swing_points(b[C.OHLC], left=2, right=2)
    sh = np.flatnonzero(sw["swing_high"].to_numpy())
    sl = np.flatnonzero(sw["swing_low"].to_numpy())
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    tgt = np.full(len(ev), np.nan)
    for i, (e, j, d) in enumerate(zip(ev["ext_pos"].to_numpy(), ev["conf_pos"].to_numpy(),
                                      ev["direction"].to_numpy())):
        arr, px = (sh, H) if d == "bullish" else (sl, L)
        k = np.searchsorted(arr, e, side="left") - 1          # last swing strictly before e
        while k >= 0 and arr[k] + 2 > j:                      # must be confirmed by decision
            k -= 1
        if k >= 0 and arr[k] >= e - LOOKBACK:
            tgt[i] = px[arr[k]]
    ev["target"] = tgt
    ev = ev[np.isfinite(ev["target"])].reset_index(drop=True)
    if ev.empty:
        return C.empty_frame(cols)
    out = C.to_trade_frame(ev, RR)
    sgn = out["direction"].to_numpy()
    entry = ev["confirm_close"].to_numpy(dtype=float)
    risk = np.abs(entry - ev["protected_swing"].to_numpy(dtype=float))
    room = sgn * (ev["target"].to_numpy() - entry)
    out["room_R"] = np.where(risk > 0, room / np.where(risk > 0, risk, 1.0), -np.inf)
    out["room_ok"] = out["room_R"] >= MIN_ROOM_R
    return out


PARAMS_SOURCE = {
    "baseline": "method_spec: §4.2 CISD as in cisd reading a (15m, series_open, POI on, 2/2, "
                "max_wait 3, protected-swing stop, 2R, 10-bar hold) — phase3 §1.8-1.13",
    "target_def": "declared-before-run: short-term target = most recent confirmed opposite-side "
                  "2/2 swing before the extreme within the phase-3 POI range lookback (40 bars)",
    "min_room_R": "declared-before-run: 1R, from the concept's own measurable 'CISD level leaves "
                  "less than 1R to the target'",
    "entry_ref": "declared-before-run: the closure price (entry) is compared with the target — "
                 "'waiting for that closure means entering at the target'",
    "max_hold": "phase3: §1.13 10 entry-TF bars",
}


if __name__ == "__main__":
    ev = cl.cache_frame(f"eo01a_skip_target_{TF}_lb{LOOKBACK}_r{MIN_ROOM_R}",
                        lambda: detect(cl.load_m1()))
    print("events", len(ev), "room_ok share", ev["room_ok"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "room_ok", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "n_gated", "gate_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "baseline: 15m CISD (series_open, 2/2, max_wait 3, min_series 1) with POI gate on, "
        "decided at confirm close, stop protected swing, 2R, 150min",
        "target: last confirmed opposite-side 2/2 swing before the extreme (<=40 bars back, "
        "confirmed by the decision); rows without one dropped",
        "gate room_ok: direction*(target - closure) >= 1R (R = |closure - protected swing|); "
        "False = CISD at/beyond the target => skip"],
        "params": {"baseline": "cisd_a", "target_def": "last_opp_swing_2/2", "lookback": LOOKBACK,
                   "min_room_R": MIN_ROOM_R, "entry_ref": "closure", "max_hold": MAX_HOLD}}
    ps = dict(PARAMS_SOURCE, lookback="phase3: poi_gate range lookback 40 bars")
    p = cl.write_result("cisd-skip-at-target", None, res, operationalization=op,
                        params_source=ps, script=__file__, probe=probe)
    print("wrote", p)
