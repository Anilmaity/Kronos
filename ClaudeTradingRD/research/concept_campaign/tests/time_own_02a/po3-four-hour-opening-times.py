"""po3-four-hour-opening-times (TTrades own voice, contested on the grid).  The if-then:
'if 6 a.m. forms a reversal, we can look for 10:00 a.m. ... that candle 3 continuation'
(R_KRKwYpzdE), with stop 'on the opposing candle' and target 2R.  A full entry/stop/target
-> trade_test.  Two readings = the two grids the concept says differ by asset class:

(a) futures grid (18/22/02/06/10/14 NY): the 06:00 4H candle is a C2 reversal vs the 02:00
    candle -> trade the 10:00 candle in the reversal direction.
(b) forex grid (17/21/01/05/09/13 NY; the grid method_spec locks, weakly, for gold): the
    05:00 candle is a C2 reversal vs the 01:00 candle -> trade the 09:00 candle.

C2 (method_spec §3.2): bullish = low < prev low AND close > prev low; bearish = high > prev
high AND close < prev high; both-sided candles skipped (direction undefined).
Entry: decide at the C2 close (= the continuation candle's open), next M1 open.  Stop: the
C2 wick extreme.  Target: 2R.  Max hold: 4h = the continuation candle's life.
The T-spot / hourly-5m refinement is not modelled (entry at the candle open).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
from _common import cl, show  # noqa: E402

GRIDS = {"a": ("futures", 6), "b": ("forex", 5)}


def make_detect(grid, c2_hour):
    def detect(m1):
        b = cl.build_bars(m1, "4h", grid4h=grid)
        st = pd.DatetimeIndex(b.index)
        hr = cl.to_ny(st).hour.to_numpy()
        pos = np.flatnonzero(hr == c2_hour)
        pos = pos[pos >= 1]
        prev = pos - 1
        contig = (st[pos] - st[prev]) == pd.Timedelta("4h")
        pos, prev = pos[contig], prev[contig]
        H, L, C = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
        bull = (L[pos] < L[prev]) & (C[pos] > L[prev])
        bear = (H[pos] > H[prev]) & (C[pos] < H[prev])
        one = bull ^ bear
        pos, bull = pos[one], bull[one]
        ct = pd.DatetimeIndex(b["close_time"].iloc[pos]).tz_convert("UTC")
        return pd.DataFrame({"decision_time": ct, "available_at": ct,
                             "direction": np.where(bull, 1, -1),
                             "stop_px": np.where(bull, L[pos], H[pos]).astype(float),
                             "rr": 2.0})
    return detect


if __name__ == "__main__":
    for reading, (grid, hr) in GRIDS.items():
        det = make_detect(grid, hr)
        ev = cl.cache_frame(f"to02a_po3_{grid}_{hr}", lambda: det(cl.load_m1()))
        print(reading, grid, len(ev), "events; long share", (ev["direction"] == 1).mean())
        probe = cl.probe_lookahead(det, ev, lookback="10D")
        res = cl.trade_test(ev, max_hold="4h")
        show(res)
        nxt = (hr + 4) % 24
        op = {"rules": [f"4H bars on the {grid} grid (New York, DST-aware)",
                        f"C2 = the {hr:02d}:00 candle vs the contiguous {(hr - 4) % 24:02d}:00 candle: bullish low<prev low & close>prev low; bearish high>prev high & close<prev high; two-sided skipped",
                        f"decide at the C2 close ({nxt:02d}:00 NY), enter next M1 open in the reversal direction (the {nxt:02d}:00 candle-3 continuation)",
                        "stop = C2 wick extreme; target 2R; exit after 4h (end of the continuation candle)"],
              "params": {"grid4h": grid, "c2_candle": f"{hr:02d}:00", "continuation_candle": f"{nxt:02d}:00",
                         "rr": 2.0, "stop": "C2 extreme", "max_hold": "4h"}}
        src = {"grid4h": ("corpus: FAKWJ-1NlLE futures 02/06/10/14 grid" if grid == "futures" else
                          "corpus: FAKWJ-1NlLE 'you can see how those timings are a bit different from futures' (forex 17/21/01/09); method_spec §1.4 forex grid for gold"),
               "c2_candle": ("corpus: R_KRKwYpzdE 'if 6 a.m. forms a reversal, we can look for 10:00 a.m.'" if grid == "futures" else
                             "declared-before-run: forex-grid analogue of the 06:00->10:00 pair (the candle one slot before the grid's 09:00 open)"),
               "continuation_candle": "corpus: R_KRKwYpzdE 'That would be that candle 3 continuation or the continuation expansion candle'",
               "rr": "corpus: po3-four-hour-opening-times.yaml 'Stop on the opposing candle or on the fair value gap; target 2R'",
               "stop": "corpus: po3-four-hour-opening-times.yaml 'Stop on the opposing candle'; method_spec §3.2 C2 test",
               "max_hold": "declared-before-run: the continuation candle's 4h life"}
        print(cl.write_result("po3-four-hour-opening-times", reading, res, operationalization=op,
                              params_source=src, script=__file__, probe=probe))
