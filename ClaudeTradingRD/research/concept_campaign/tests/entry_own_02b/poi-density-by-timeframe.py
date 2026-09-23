"""poi-density-by-timeframe — batch entry_own_02b.

c7nk7ypJHN4: on the hourly (~24 candles a day) a point of interest is REQUIRED as
the filter that says which candle matters ("you're going to want a point of interest
here"); YAML measurable: "expectancy of hourly models with versus without a POI".

Test: gate_test on the phase-3 rung-0 1h CISD book (series_open, 2/2, max_wait 3,
stop = protected swing, 2R, 10h). Gate = the method-spec §4.1 POI gate
(detectors.poi.poi_gate, timeframe='1h' -> required, setup 'reversal'), evaluated on
bars up to and including the confirming bar ONLY (the 50%-body-hold branch cannot
look past the decision). claim '+': POI-passing hourly models beat the rest.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                    # noqa: E402
from detectors.cisd import cisd_events                      # noqa: E402
from detectors.poi import poi_gate                          # noqa: E402

TF = "1h"
MAX_HOLD = "10h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "poi_ok"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 3000:
        return pd.DataFrame(columns=COLS)
    b = cl.build_bars(m1, TF)
    ohlc = b[["open", "high", "low", "close"]]
    ev = cisd_events(ohlc, level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=COLS)
    last_ok = m1.index[-1] + pd.Timedelta("1min")
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    keep = np.asarray(close <= last_ok)
    ev, close = ev[keep].reset_index(drop=True), close[keep]
    pos = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    poi = np.zeros(len(ev), bool)
    for r, (p, et, dr) in enumerate(zip(pos, ev["extreme_time"], ev["direction"])):
        res = poi_gate(ohlc.iloc[:p + 1], et, dr, timeframe="1h", setup_type="reversal")
        poi[r] = bool(res.passed)
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": np.where(ev["direction"] == "bullish", 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0,
                         "poi_ok": poi})


OP = {"rules": [
    "baseline: 1h bare CISD (series_open close-through, fractal 2/2, within 3 bars), decide at the confirming bar close, "
    "stop = protected swing, 2R, 10h (phase-3 rung 0)",
    "gate: detectors.poi.poi_gate (method spec §4.1 search order FVG -> swing taken -> CISD level + 50% body hold; "
    "both FVG and swing tagged when both exist; range from the last opposing swing, lookback 40), timeframe 1h => "
    "required, evaluated on bars <= the confirming bar"],
    "params": {"tf": TF, "cisd": "series_open 2/2 max_wait 3", "rr": 2.0, "max_hold": MAX_HOLD,
               "poi_gate": "detectors.poi defaults (lookback 40, polarity any, body_hold_bars 5 truncated at decision)"}}
SRC = {"tf": "corpus: c7nk7ypJHN4 'you're going to want a point of interest here' (the hourly)",
       "cisd": "phase3: rung-0 locked config",
       "rr": "phase3: rung-0 locked 2R",
       "max_hold": "phase3: 10 entry-TF bars",
       "poi_gate": "method_spec: §4.1 point-of-interest gate as implemented in detectors/poi.py"}

if __name__ == "__main__":
    ev = cl.cache_frame("poi_density_1h_cisd", lambda: detect(cl.load_m1()))
    print(len(ev), ev["poi_ok"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "poi_ok", mask_available_at="decision_time", max_hold=MAX_HOLD)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
                                   "ties", "ctrl_overlap", "sanity")})
    cl.write_result("poi-density-by-timeframe", None, res, operationalization=OP, params_source=SRC,
                    script=__file__, probe=probe,
                    notes="Tests the hourly half of the density claim (POI required on 1h). The 4h half ('acceptable "
                          "without') is a permission, not a directional claim, and was not run.")
