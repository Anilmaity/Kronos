"""cisd — Change In The State Of Delivery, as TTrades defines it (POI is part of the definition).

Concept: concepts/entry/cisd.yaml (contested: WHICH price of the opposing series is closed through).
Test: trade_test — entry at market on the confirming close, stop at the protected swing (the extreme),
2R target (execution.stop / 'minimum 2R'), 15m entry TF (his favourite 4H/15m pairing), POI gate ON
(the extreme must have tagged an FVG / taken a swing / held the 50%-body CISD level: §4.1).

Readings (the contested level, at most two):
  a  series_open    — close beyond the OPEN of the FIRST candle of the run (method-spec default,
                      "Mark out the opening price in that series").
  b  series_extreme — close beyond the WHOLE series (its high for a bullish case), the literal
                      wording of hourly-cisd-confirmation ("close above the high of that series").
All parameters declared before the first run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402

TF = "15min"
MAX_HOLD = "150min"
RR = 2.0


def make_detect(level_rule: str):
    def detect(m1):
        _, ev = C.cisd_with_poi(m1, TF, level_rule=level_rule, max_wait=3, min_series=1)
        cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
        if ev.empty:
            return C.empty_frame(cols)
        ev = ev[ev["poi_passed"]].reset_index(drop=True)
        if ev.empty:
            return C.empty_frame(cols)
        return C.to_trade_frame(ev, RR)
    return detect


PARAMS_SOURCE = {
    "tf": "method_spec: §1.3 favourite stack Daily/4H/15m — 15m is the CISD entry TF",
    "swing": "phase3: meta/conjunction_preregistration.md §1.8 swing left=2,right=2",
    "max_wait": "phase3: §1.8 max_wait=3 ('I prefer 1, 2, maybe three', v-shape-reversal-speed)",
    "min_series": "phase3: §1.8 min_series=1 (dedicated model video accepts one candle)",
    "poi_gate": "method_spec: §4.2 point 2 / §4.1 — POI required as part of his definition; "
                "phase3 poi_gate defaults (range lookback 40, fvg polarity any, both-when-both)",
    "stop": "method_spec: §5.1 / cisd.yaml execution.stop — protected swing (the extreme)",
    "rr": "phase3: §1.12 2R fixed ('minimum 2R', risk-reward-minimum)",
    "max_hold": "phase3: §1.13 10 entry-TF bars",
    "level_rule": "method_spec: §4.2 [P] — reading a first-candle open (default); reading b the "
                  "series' far extreme, per hourly-cisd-confirmation.yaml 'close above the high "
                  "of that series'",
}


def run(reading: str, level_rule: str):
    detect = make_detect(level_rule)
    ev = cl.cache_frame(f"eo01a_cisd_{level_rule}_{TF}_mw3_poi", lambda: detect(cl.load_m1()))
    print(reading, level_rule, "events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties", "ctrl_overlap"):
        print(" ", k, res.get(k))
    op = {"rules": [
        f"{TF} bars (UTC-aligned); CISD via detectors.cisd.cisd_events level_rule={level_rule}, "
        "swing 2/2, max_wait 3, min_series 1",
        "POI gate (detectors.poi.poi_gate, timeframe 15min => required) evaluated on bars up "
        "to the confirming bar only; keep passes",
        "decide at confirming bar close; enter next M1 open; stop at protected swing; 2R; "
        f"time exit {MAX_HOLD}"],
        "params": {"tf": TF, "swing": "2/2", "max_wait": 3, "min_series": 1, "poi_gate": "on",
                   "stop": "protected_swing", "rr": RR, "max_hold": MAX_HOLD,
                   "level_rule": level_rule}}
    p = cl.write_result("cisd", reading, res, operationalization=op, params_source=PARAMS_SOURCE,
                        script=__file__, probe=probe,
                        notes="Phase-3 R0 (bare CISD, POI off) was NULL on 15m; this is the "
                              "POI-on corpus definition as a standalone trade book.")
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run("a", "series_open")
    if "b" in which:
        run("b", "series_extreme")
