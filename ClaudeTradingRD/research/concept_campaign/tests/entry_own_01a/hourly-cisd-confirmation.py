"""hourly-cisd-confirmation — a 1H close through the series that made the day's extreme confirms the daily wick.

Concept: concepts/entry/hourly-cisd-confirmation.yaml (contested). Rules: "On the 1H chart, restrict
attention to the price action inside the candidate daily candle." "Bullish case: find the low. Identify
the consecutive series of down-close candles that made that low. Require a 1H close above the high of that
series of down-close candles." Mirror for bearish. "Only after that close-through is the daily wick
considered confirmed." Execution: entry after the close-through; stop beyond the confirmed extreme.

Test: trade_test. Detector (pure, causal): for each NY trading day (18:00 roll), walk the 1H bars; track
the day's running low (high); when a new extreme prints, find the consecutive run of down-close
(up-close) 1H candles that made it inside the day (the extreme bar itself or the run ending within 2 bars
before it, max 10 candles — detectors.cisd._run_into_extreme's rule); the first later 1H bar that closes
through the level fires one event for that extreme (a new extreme re-arms). Decide at that bar's close,
enter next M1 open, stop at the day's extreme, 2R, 10h hold.

Readings (contested level):
  a  close above the HIGH of the series (bearish: below its low) — this concept's own wording.
  b  close above the OPEN of the first candle of the series — the order-block formulation the
     ambiguity list says is "not restated here" (method-spec §4.2 default).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402

TF = "1h"
MAX_HOLD = "10h"
RR = 2.0
MAX_SERIES = 10


def _run(o, c, i, day_start, bullish):
    """Run of opposing-close candles producing the extreme at i, inside the day (>= day_start)."""
    def q(k):
        return (c[k] < o[k]) if bullish else (c[k] > o[k])
    end = i
    while end > day_start and not q(end):
        end -= 1
        if i - end > 2:
            return -1, -1
    if not q(end):
        return -1, -1
    start = end
    while start > day_start and q(start - 1) and (end - start + 1) < MAX_SERIES:
        start -= 1
    return start, end


def make_detect(level_kind: str):
    def detect(m1):
        cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
        b = cl.build_bars(m1, TF)
        if len(b) < 3:
            return C.empty_frame(cols)
        o, h, l, c = (b[k].to_numpy(dtype=float) for k in C.OHLC)
        ct = pd.DatetimeIndex(b["close_time"])
        day = cl.trading_day(b.index).to_numpy()
        rows = []
        n = len(b)
        for bullish in (True, False):
            ds = 0
            ext = np.nan
            pos = -1
            level = np.nan
            fired = True
            for j in range(n):
                if j == 0 or day[j] != day[j - 1]:
                    ds, ext, pos, fired, level = j, np.nan, -1, True, np.nan
                x = l[j] if bullish else h[j]
                if pos < 0 or (x < ext if bullish else x > ext):
                    ext, pos, fired = x, j, False
                    s, e = _run(o, c, j, ds, bullish)
                    if s < 0:
                        level, fired = np.nan, True
                    elif level_kind == "series_extreme":
                        level = h[s:e + 1].max() if bullish else l[s:e + 1].min()
                    else:
                        level = o[s]
                    continue
                if not fired and j > pos:
                    if (c[j] > level) if bullish else (c[j] < level):
                        rows.append((ct[j], 1 if bullish else -1, ext))
                        fired = True
        if not rows:
            return C.empty_frame(cols)
        rows.sort(key=lambda r: (r[0], r[1]))
        t = pd.DatetimeIndex([r[0] for r in rows])
        return pd.DataFrame({"decision_time": t, "available_at": t,
                             "direction": np.array([r[1] for r in rows], dtype=int),
                             "stop_px": np.array([r[2] for r in rows], dtype=float), "rr": RR})
    return detect


PARAMS_SOURCE = {
    "tf": "corpus: hourly-cisd-confirmation.yaml 'On the 1H chart ... inside the candidate daily "
          "candle' (1D/1H pairing, method_spec §1.2)",
    "day_open_hour": "session_window_fit: 18:00 NY daily candle (settled)",
    "series_rule": "phase3: detectors.cisd run rule (extreme bar or run ending <=2 bars before it, "
                   "max 10 candles), restricted to the day",
    "level_kind": "corpus: reading a 'close above the high of that series of down-close candles'; "
                  "reading b method_spec §4.2 first-candle open",
    "stop": "corpus: execution.stop 'Beyond the confirmed extreme'",
    "rr": "phase3: §1.12 2R",
    "max_hold": "phase3: §1.13 10 entry-TF bars",
}


def run(reading, level_kind):
    detect = make_detect(level_kind)
    ev = cl.cache_frame(f"eo01a_hourly_{level_kind}", lambda: detect(cl.load_m1()))
    print(reading, level_kind, "events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties", "ctrl_overlap"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "1H bars; per NY trading day (18:00 roll) track the running low/high",
        "series = consecutive opposing-close 1H candles that made the extreme, inside the day",
        f"fire on the first 1H close through the series' {level_kind} after the extreme; a new "
        "extreme re-arms",
        "decide at that bar's close, next M1 open entry; stop at the day's extreme; 2R; 10h"],
        "params": {"tf": TF, "day_open_hour": 18, "series_rule": "run<=10,<=2 bars back",
                   "level_kind": level_kind, "stop": "day_extreme", "rr": RR,
                   "max_hold": MAX_HOLD}}
    p = cl.write_result("hourly-cisd-confirmation", reading, res, operationalization=op,
                        params_source=PARAMS_SOURCE, script=__file__, probe=probe)
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run("a", "series_extreme")
    if "b" in which:
        run("b", "series_open")
