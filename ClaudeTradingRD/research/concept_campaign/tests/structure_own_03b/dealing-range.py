"""dealing-range (TTrades, CAuN4tvLInQ) — gate_test.

The concept is a definition (nearest high/low bounding price at the working zoom, 0.5
splits premium from discount, a range price has left is discarded). Its only decision
consequence is the premium/discount split of THAT range, so the test is: do longs taken in
the discount (shorts in the premium) of the dealing range beat the rest of the book? '+'.

Operationalisation (declared before the first run):
  * zoom = the entry timeframe, 15m. Candidate highs/lows = confirmed 15m fractal (2/2)
    swings whose swing bar lies within the last 48 15m bars (three 4H candles: the
    method spec's relevant-swing look-back of three higher-timeframe candles).
  * dealing range at a decision = the MOST RECENT candidate swing high that no later closed
    bar has traded above, and the most recent candidate swing low no later bar has traded
    below ("a dealing range whose extremes price has left behind is discarded").
    If either side has no such swing inside the look-back, price is outside every range at
    this zoom and the event is dropped from the book (it would need a wider zoom).
  * EQ = midpoint (wicks). Gate: long with confirming close < EQ, short with close > EQ.
  * baseline = phase-3 rung-0 15m CISD, stop protected swing, 2R, 150min time exit.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

MAX_HOLD = "150min"
LOOKBACK = 48


def detect(m1):
    ev, b = C.cisd_book(m1, "15min")
    sw = swing_points(b[["high", "low"]], 2, 2)
    h, lo = b["high"].to_numpy(float), b["low"].to_numpy(float)
    ish, isl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    rh = np.full(len(ev), np.nan)
    rl = np.full(len(ev), np.nan)
    for r, (k, px) in enumerate(zip(ev["bar_pos"].to_numpy(), ev["px"].to_numpy())):
        for i in range(k - 2, max(k - LOOKBACK, 0) - 1, -1):     # confirmed: i + 2 <= k
            if ish[i] and h[i] >= px and h[i + 1:k + 1].max() <= h[i]:
                rh[r] = h[i]
                break
        for i in range(k - 2, max(k - LOOKBACK, 0) - 1, -1):
            if isl[i] and lo[i] <= px and lo[i + 1:k + 1].min() >= lo[i]:
                rl[r] = lo[i]
                break
    ok = ~np.isnan(rh) & ~np.isnan(rl)
    ev = ev[ok].reset_index(drop=True)
    eq = (rh[ok] + rl[ok]) / 2
    d, px = ev["direction"].to_numpy(), ev["px"].to_numpy()
    ev["dr_high"], ev["dr_low"] = rh[ok], rl[ok]
    ev["in_half"] = ((d == 1) & (px < eq)) | ((d == -1) & (px > eq))
    return ev.drop(columns=["bar_pos"])


if __name__ == "__main__":
    ev = cl.cache_frame("dealing_range_cisd15_lb48", lambda: detect(cl.load_m1()))
    print(len(ev), ev.in_half.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "in_half", mask_available_at="decision_time", max_hold=MAX_HOLD)
    C.show(res)
    p = cl.write_result(
        "dealing-range", None, res,
        operationalization={"rules": [
            "zoom = entry TF 15m; candidates = confirmed 2/2 swings whose bar is within the last 48 15m bars",
            "dealing range = most recent candidate swing high not traded above since, and most recent swing low not traded below since, bounding the decision close; no such pair -> event dropped",
            "EQ = midpoint (wicks); gate: long below EQ / short above EQ",
            "baseline: 15m rung-0 CISD (series_open, 2/2, max_wait 3), stop protected swing, 2R, 150min exit"],
            "params": {"zoom_tf": "15min", "swing": "2/2", "lookback_bars": LOOKBACK,
                       "baseline_tf": "15min", "max_wait": 3, "rr": 2.0, "max_hold": MAX_HOLD}},
        params_source={
            "zoom_tf": "declared-before-run: the zoom level matching the entry timeframe (concept precondition)",
            "swing": "phase3: swing_points left=2 right=2",
            "lookback_bars": "method_spec: §1.1 relevant-swing look-back = three higher-timeframe candles (15m -> 3 x 4H = 48 bars)",
            "baseline_tf": "phase3: primary stack entry TF",
            "max_wait": "phase3: locked CISD config max_wait=3",
            "rr": "phase3: locked 2R target",
            "max_hold": "phase3: 10 entry-TF bars"},
        script=__file__, probe=probe,
        notes="'Zoom your screen in' is fixed as the 15m entry TF with a 48-bar look-back; events with no bounding unbroken swing pair are dropped.")
    print(p)
