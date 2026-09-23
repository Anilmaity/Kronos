"""protected-swing — the invalidation level, traded as the model trades it (contested).

Concept: concepts/structure/protected-swing.yaml; method_spec §3.8.

Construction (trade_test): point of interest -> closure through the series of opposing
candles that made the extreme. On 1h bars (concept ltf list 1H):
  * the extreme = a 2/2 fractal swing low (high) and the contiguous run of down-close
    (up-close) candles into it (detectors.cisd, min_series 1);
  * POI, strict: the extreme must have SWEPT a prior swing or REACHED INTO an FVG
    ("we have to sweep out a low or reach into a gap", G1IIdQ3RAkY) — detectors.poi with
    either branch sufficient; the CISD-level / 0.5-of-opposing-candle fallback is NOT
    accepted (an extreme with no important level "is not a protected swing at all");
  * the closure through must arrive within 3 bars ("1, 2, maybe three");
  * entry at the next M1 open after the closing bar ("printed at the open of the next
    candle"), stop ON the protected swing, target 2R ("put my stop on the protected swing
    high, and then look for 2R", sAh3ZMkzzpQ), 10h hold (phase-3 10 bars).
The contested clause (ambiguities list): "Whether the close must be through the series'
opening price or through its extreme".
  reading a: close through the OPENING price of the series (first candle's open)
  reading b: close through the series' far EXTREME (its high, bullish case)
All parameters declared before the first run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402
from detectors.cisd import cisd_events      # noqa: E402
from detectors.poi import poi_gate          # noqa: E402

CID = "protected-swing"
TF = "1h"
WIN = 200          # local bar window handed to the POI gate (range lookback is 40)
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def make_detect(level_rule: str):
    def detect(m1):
        b = cl.build_bars(m1, TF)
        if len(b) < 10:
            return C.empty_frame(COLS)
        o = b[C.OHLC]
        ev = cisd_events(o, level_rule=level_rule, left=2, right=2, max_wait=3, min_series=1)
        if ev.empty:
            return C.empty_frame(COLS)
        ext = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
        conf = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
        keep = np.zeros(len(ev), bool)
        for k, (e, j, dr) in enumerate(zip(ext, conf, ev["direction"].to_numpy())):
            s0 = max(0, j - WIN)
            sub = o.iloc[s0: j + 1]                    # nothing after the closing bar
            r = poi_gate(sub, int(e - s0), dr, timeframe=TF, setup_type="reversal",
                         require_both_when_both_exist=False, level_rule=level_rule)
            keep[k] = bool(r.passed) and (r.kind_used in ("fvg", "swing"))
        ct = pd.DatetimeIndex(b["close_time"].to_numpy()[conf])
        out = pd.DataFrame({"decision_time": ct, "available_at": ct,
                            "direction": np.where(ev["direction"].to_numpy() == "bullish", 1, -1),
                            "stop_px": ev["protected_swing"].to_numpy(dtype=float),
                            "rr": 2.0})
        return out[keep].reset_index(drop=True)
    return detect


PARAMS_SOURCE = {
    "tf": "declared-before-run: 1h (concept ltf list; the 15m POI-on CISD book is the cisd "
          "concept's test)",
    "swing": "phase3: §1.8 swing left=2,right=2",
    "min_series": "corpus: tDiwwMRWF2k 'in one example the series is a single candle'",
    "max_wait": "phase3: §1.8 max_wait=3 (v-shape-reversal-speed '1, 2, maybe three')",
    "poi": "corpus: G1IIdQ3RAkY 'we have to sweep out a low or reach into a gap'; "
           "method_spec §3.8 — either branch suffices, no CISD-level fallback",
    "poi_lookback": "phase3: poi_gate defaults (range lookback 40, polarity any)",
    "level_rule": "corpus: protected-swing ambiguity 'Whether the close must be through the "
                  "series' opening price or through its extreme' — a open, b extreme",
    "stop": "corpus: sAh3ZMkzzpQ 'put my stop on the protected swing high'",
    "rr": "corpus: sAh3ZMkzzpQ 'and then look for 2R'",
    "max_hold": "phase3: §1.13 10 entry-TF bars",
}


def run(reading: str, level_rule: str):
    detect = make_detect(level_rule)
    ev = cl.cache_frame(f"so01b_ps_{level_rule}_1h", lambda: detect(cl.load_m1()))
    print(reading, level_rule, "events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.trade_test(ev, max_hold="10h")
    C.show(res)
    op = {"rules": [
        f"1h UTC-aligned bars; 2/2 swing extreme and its opposing-candle series; close "
        f"through the series level ({level_rule}) within 3 bars",
        "POI strict: extreme swept a prior swing OR reached into an FVG (detectors.poi, "
        "either branch; CISD-level fallback rejected), evaluated on bars up to the closing "
        "bar only",
        "enter next M1 open; stop on the protected swing; target 2R; 10h clock hold"],
        "params": {"tf": TF, "swing": "2/2", "min_series": 1, "max_wait": 3,
                   "poi": "sweep|fvg", "poi_lookback": 40, "level_rule": level_rule,
                   "stop": "protected_swing", "rr": 2.0, "max_hold": "10h"}}
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=PARAMS_SOURCE,
                        script=__file__, probe=probe,
                        notes="Reach/separation and 'took too long to form' quality filters "
                              "are unquantified in the corpus and not applied.")
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run("a", "series_open")
    if "b" in which:
        run("b", "series_extreme")
