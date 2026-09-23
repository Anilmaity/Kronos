"""continuation-order-block — his preferred entry: the continuation after a confirmed CISD.

Concept: concepts/entry/continuation-order-block.yaml (method spec §4.5). Rules: after an established
direction (a confirmed CISD), wait for price to (a) retrace into a fair value gap or (b) sweep a
low/high; require a close through the series of opposing candles that went into that level -> new
protected swing / order block; "Enter at the market price on the closure"; stop on the new protected
swing; "the stated minimum objective is 2R". No FVG tag and no sweep -> "nothing here for me".

Operationalisation (15m, declared before run):
  * CISD events: detectors.cisd series_open, 2/2 swing, max_wait 3, min_series 1, POI gate annotated
    on bars up to the confirming bar.
  * E1 (established direction) = the most recent POI-passing CISD whose confirmation closed before the
    candidate's extreme bar, within 40 bars of it.
  * E2 (the continuation) = a CISD in E1's direction whose extreme tagged an FVG or took a swing
    (poi kind fvg / swing / fvg+swing — NOT the CISD-level fallback), whose extreme is beyond E1's
    protected swing (higher low / lower high), with no bar between E1's confirmation and E2's
    confirmation trading through E1's protected swing.
  * Entry at market on E2's closure (next M1 open), stop at E2's protected swing, 2R, 150min.
Contested point (limit at the block vs market on the closure) — only the market reading is tested:
the harness enters at the next M1 open, and the concept states the market entry verbatim.
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
E1_WINDOW = 40


def detect(m1):
    b, ev = C.cisd_with_poi(m1, TF, level_rule="series_open", max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return C.empty_frame(cols)
    ev = ev[ev["poi_passed"]].sort_values(["conf_pos", "ext_pos"]).reset_index(drop=True)
    if ev.empty:
        return C.empty_frame(cols)
    L, H = b["low"].to_numpy(), b["high"].to_numpy()
    conf = ev["conf_pos"].to_numpy()
    ext = ev["ext_pos"].to_numpy()
    dirs = ev["direction"].to_numpy()
    prot = ev["protected_swing"].to_numpy(dtype=float)
    kinds = ev["poi_kind"].to_numpy()
    keep = np.zeros(len(ev), dtype=bool)
    for i in range(len(ev)):
        if kinds[i] not in ("fvg", "swing", "fvg+swing"):
            continue
        k = np.searchsorted(conf, ext[i], side="left") - 1        # E1: confirmed before E2's extreme
        if k < 0 or ext[i] - conf[k] > E1_WINDOW or dirs[k] != dirs[i]:
            continue
        seg = slice(conf[k] + 1, conf[i] + 1)
        if dirs[i] == "bullish":
            ok = prot[i] > prot[k] and L[seg].min() > prot[k]
        else:
            ok = prot[i] < prot[k] and H[seg].max() < prot[k]
        keep[i] = ok
    ev = ev[keep].reset_index(drop=True)
    if ev.empty:
        return C.empty_frame(cols)
    return C.to_trade_frame(ev, RR)


PARAMS_SOURCE = {
    "tf": "method_spec: §1.3 favourite stack 4H/15m (15m entry); concept ltf lists 15m",
    "cisd": "phase3: §1.8 CISD series_open, 2/2, max_wait 3, min_series 1, POI gate (§4.1)",
    "triggers": "corpus: continuation-order-block.yaml 'retrace into a fair value gap, or sweep a "
                "low/high' => poi kind fvg/swing only",
    "e1_window": "phase3: poi_gate range lookback 40 bars reused as the E1 look-back",
    "higher_low": "method_spec: §4.5 'wait for a lower high in a bearish sequence, a higher low in "
                  "a bullish one'; invalidation 'the new protected swing is taken out'",
    "entry": "corpus: continuation-order-block.yaml 'Enter at the market price on the closure'",
    "stop": "corpus: continuation-order-block.yaml 'stop on the new protected swing'",
    "rr": "corpus: continuation-order-block.yaml 'the stated minimum objective is 2R'",
    "max_hold": "phase3: §1.13 10 entry-TF bars",
}


if __name__ == "__main__":
    ev = cl.cache_frame(f"eo01a_cob_{TF}_w{E1_WINDOW}", lambda: detect(cl.load_m1()))
    print("events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties", "ctrl_overlap"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "15m CISD events (series_open, 2/2, max_wait 3, min_series 1) with POI gate",
        "E1 = latest POI-passing CISD confirmed before the candidate's extreme, <=40 bars earlier",
        "continuation = same-direction CISD whose extreme tagged an FVG or swept a swing, extreme "
        "beyond E1's protected swing, E1's protected swing not traded through before confirmation",
        "enter at market on the closure (next M1 open); stop new protected swing; 2R; 150min"],
        "params": {"tf": TF, "cisd": "series_open/2-2/mw3/ms1", "triggers": "fvg|swing",
                   "e1_window": E1_WINDOW, "higher_low": True, "entry": "market_on_close",
                   "stop": "new_protected_swing", "rr": RR, "max_hold": MAX_HOLD}}
    p = cl.write_result("continuation-order-block", None, res, operationalization=op,
                        params_source=PARAMS_SOURCE, script=__file__, probe=probe,
                        notes="Only the market-on-closure entry reading tested; the limit-at-block "
                              "retest reading is not representable with next-M1-open entries.")
    print("wrote", p)
