"""early-cisd — a CISD inside a still-open HTF candle is unconfirmed; wait for the HTF closure.

Concept: concepts/entry/early-cisd.yaml. "A CISD forms inside the still-open higher-timeframe candle ->
early CISD (dotted / unconfirmed)." "On the higher-timeframe closure the model confirms." "Trade it only
on a strong bias; the default posture is to wait for the actual continuation." Measurable: "R difference
between early-CISD entries and post-closure continuation entries".

Test: gate_test, claim '+' = CISDs taken AFTER the HTF closure has confirmed the model beat early ones.
Pairing 4H (forex grid) / 15m (his favourite). Baseline = 15m CISD events (series_open, 2/2, max_wait 3,
POI on, protected-swing stop, 2R, 150min) whose extreme printed inside the current 4H candle k, split:
  confirmed (mask True): the last CLOSED 4H candle k-1 is a C2 in the CISD direction
      (bullish: low[k-1] < low[k-2] and close[k-1] > low[k-2]) -> the CISD is the continuation in C3.
  early (mask False): k-1 is not such a C2, but the still-open candle k is forming one at the decision
      (bullish: running low of k < low[k-1] and the confirming close > low[k-1]).
Events that are neither are outside the concept and dropped. Mirror for bearish.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402

TF = "15min"
HTF = "4h"
MAX_HOLD = "150min"
RR = 2.0


def detect(m1):
    b, ev = C.cisd_with_poi(m1, TF, level_rule="series_open", max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "confirmed"]
    if ev.empty:
        return C.empty_frame(cols)
    ev = ev[ev["poi_passed"]].reset_index(drop=True)
    if ev.empty:
        return C.empty_frame(cols)
    ctx = C.htf_context(b, m1, HTF)
    j = ev["conf_pos"].to_numpy()
    x = ctx.iloc[j].reset_index(drop=True)
    bull = ev["direction"].to_numpy() == "bullish"
    in_k = (pd.DatetimeIndex(ev["extreme_time"]) >= pd.DatetimeIndex(x["htf_start"])) & x["valid"].to_numpy()
    cc = ev["confirm_close"].to_numpy(dtype=float)
    c2_prev = np.where(bull,
                       (x["p1_low"] < x["p2_low"]) & (x["p1_close"] > x["p2_low"]),
                       (x["p1_high"] > x["p2_high"]) & (x["p1_close"] < x["p2_high"]))
    c2_forming = np.where(bull,
                          (x["run_low"].to_numpy() < x["p1_low"].to_numpy()) & (cc > x["p1_low"].to_numpy()),
                          (x["run_high"].to_numpy() > x["p1_high"].to_numpy()) & (cc < x["p1_high"].to_numpy()))
    confirmed = in_k & c2_prev
    early = in_k & ~c2_prev & c2_forming
    sel = confirmed | early
    ev = ev[sel].reset_index(drop=True)
    if ev.empty:
        return C.empty_frame(cols)
    out = C.to_trade_frame(ev, RR)
    out["confirmed"] = np.asarray(confirmed[sel], dtype=bool)
    return out


PARAMS_SOURCE = {
    "pairing": "method_spec: §1.3 favourite stack — 4H structure / 15m CISD entry",
    "grid4h": "session_window_fit: forex grid 17/21/01/05/09/13 NY (default for gold)",
    "c2_rule": "phase3: §1.7 C2 bullish low[i]<low[i-1] and close[i]>low[i-1] (mirror bearish)",
    "cisd": "phase3: §1.8 series_open, 2/2, max_wait 3, min_series 1, POI gate on",
    "early_def": "declared-before-run: early = CISD in the open 4H candle that is forming a C2 at the "
                 "decision (swept the prior candle's extreme, confirm close back inside) while the "
                 "last closed candle is not a same-direction C2",
    "rr": "phase3: §1.12 2R",
    "max_hold": "phase3: §1.13 10 entry-TF bars",
}


if __name__ == "__main__":
    ev = cl.cache_frame(f"eo01a_early_{TF}_{HTF}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "confirmed share", ev["confirmed"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "confirmed", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "15m CISD (series_open, 2/2, mw3, ms1) with POI gate, extreme inside current 4H candle",
        "confirmed = last closed 4H candle is a same-direction C2 (CISD is in its C3)",
        "early = open 4H candle forming a same-direction C2 at the decision; last closed is not",
        "decide at confirm close; stop protected swing; 2R; 150min; gate = confirmed"],
        "params": {"pairing": "4H/15m", "grid4h": "forex", "c2_rule": "phase3", "cisd": "phase3",
                   "early_def": "forming_c2", "rr": RR, "max_hold": MAX_HOLD}}
    p = cl.write_result("early-cisd", None, res, operationalization=op,
                        params_source=PARAMS_SOURCE, script=__file__, probe=probe)
    print("wrote", p)
