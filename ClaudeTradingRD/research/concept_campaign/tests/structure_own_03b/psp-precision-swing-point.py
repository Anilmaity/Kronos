"""psp-precision-swing-point (TTrades ZAEgtvsD-qQ / sdZkE-naNiY; GxTradez 3eVxTV_7L2U) — gate_test, 2 readings.

Claim: a PSP (the same candle closing opposite colours on two correlated markets) adds
confidence to a valid fractal-model C2 — "surfaced only as C2 plus a PSP". '+' = C2s with
a PSP beat C2s without one. Correlate for gold: silver (XAG_USD, OANDA H1), the correlate
phase 3 used; H1 is the finest the correlate file supports (concept htf 4H/1H).

Operationalisation (declared before the first run):
  * baseline book = gold 1H C2 (detectors.fractal.c2_events: sweep of the prior candle's
    extreme, close back inside, reversal-coloured close), on the gold/silver inner-joined
    H1 grid. Decide at the C2 close; trade the reversal; stop = the C2 extreme; 2R; 10h.
  * reading a = CANDLE TWO PSP: silver's same-hour candle closes the opposite colour to
    gold's C2 (strictly: one up, one down; a flat close is not a PSP).
  * reading b = CANDLE ONE PSP: on the candle before C2 (C1) gold and silver close
    opposite colours.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402
from detectors.fractal import c2_events  # noqa: E402

MAX_HOLD = "10h"


def detect(m1):
    P = C.pair_h1(m1)
    g = P.rename(columns={"g_open": "open", "g_high": "high", "g_low": "low",
                          "g_close": "close"})[["open", "high", "low", "close"]]
    ev = c2_events(g, sweep_ref="prior_candle", require_close_inside=True,
                   require_reversal_close=True)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "psp_c2", "psp_c1"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    pos = P.index.get_indexer(pd.DatetimeIndex(ev["time"]))
    ok = pos >= 1
    ev, pos = ev[ok].reset_index(drop=True), pos[ok]
    gcol = np.sign(P["g_close"].to_numpy() - P["g_open"].to_numpy())
    scol = np.sign(P["s_close"].to_numpy() - P["s_open"].to_numpy())
    ct = pd.DatetimeIndex(P["close_time"])
    d = np.where(ev["direction"] == "bullish", 1, -1)
    out = pd.DataFrame({
        "decision_time": ct[pos], "available_at": ct[pos], "direction": d,
        "stop_px": np.where(d == 1, ev["low"].to_numpy(float), ev["high"].to_numpy(float)),
        "rr": 2.0,
        "psp_c2": (gcol[pos] * scol[pos]) < 0,
        "psp_c1": (gcol[pos - 1] * scol[pos - 1]) < 0,
    })
    return out.drop_duplicates(subset=["decision_time", "direction"]).sort_values(
        "decision_time").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("psp_c2book_1h_xag", lambda: detect(cl.load_m1()))
    print(len(ev), ev.psp_c2.mean(), ev.psp_c1.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    base = ["gold/silver (OANDA XAG_USD H1) inner-joined on gold 1H labels",
            "baseline: gold 1H C2 = sweep of prior candle extreme, close back inside, reversal-coloured close; decide at C2 close, trade the reversal, stop C2 extreme, 2R, 10h"]
    params = {"tf": "1h", "correlate": "XAG_USD", "sweep_ref": "prior_candle", "rr": 2.0,
              "max_hold": MAX_HOLD}
    src = {"tf": "corpus: ZAEgtvsD-qQ timeframes htf 4H/1H; 1H is the finest the correlate supports",
           "correlate": "corpus: gold-correlated-assets (silver); phase3 load_correlate XAG_USD",
           "sweep_ref": "phase3: C2 detector default (prior candle)",
           "rr": "phase3: locked 2R target",
           "max_hold": "phase3: 10 entry-TF bars"}
    for rd, col, rule in (("a", "psp_c2", "gate a (candle two PSP): silver's C2-hour candle closes the opposite colour to gold's"),
                          ("b", "psp_c1", "gate b (candle one PSP): on the hour before C2, gold and silver close opposite colours")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=MAX_HOLD)
        print("reading", rd)
        C.show(res)
        p = cl.write_result(
            "psp-precision-swing-point", rd, res,
            operationalization={"rules": base + [rule], "params": params},
            params_source=src, script=__file__, probe=probe,
            notes="PSP tested only as 'C2 plus a PSP' (TTrades' own scope); GxTradez's standalone-reversal framing is not separately traded. Readings = the two named PSP types.")
        print(p)
