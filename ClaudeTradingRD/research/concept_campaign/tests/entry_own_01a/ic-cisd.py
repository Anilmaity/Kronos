"""ic-cisd — intracandle CISD: a LTF CISD inside the continuation HTF candle marks its wick as formed.

Concept: concepts/entry/ic-cisd.yaml (method spec §4.3). Rules: inside the continuation candle, wait for
price to reach a point of interest against the intended direction; require a close through the series of
opposing candles (the CISD) -> protected swing inside the HTF candle; "treat the higher-timeframe wick as
complete and trade the body away from it". "TIMING RULE: it is ideal for the IC-CISD to form EARLY in the
candle ... If it forms late ... wait for the NEXT candle." "The CISD must occur off a point of interest; if
no FVG or high/low exists, the CISD level itself is used." Execution: entry on the close; stop on the
intracandle protected swing; 2R.

Operationalisation (declared before run), 4H (forex grid) / 15m:
  * HTF direction of the open 4H candle k from the previous-candle engine on the last two CLOSED
    candles: bullish if k-1 is a bullish C2 (low[k-1]<low[k-2], close[k-1]>low[k-2]) or closed above
    high[k-2]; mirror bearish; rows where both directions qualify are dropped.
  * IC-CISD = 15m CISD (series_open, 2/2, max_wait 3, min_series 1) in that direction, POI gate
    passed (FVG / swing / CISD-level fallback), whose extreme printed inside candle k and beyond
    k's open against the direction (the wick side).
  * early = decided within the first half (2h) of the 4H candle.
Readings:
  a  trade_test of the rule as stated: early IC-CISDs only (late ones are skipped), entry at market on
     the close, stop protected swing, 2R, 150min.
  b  gate_test of the timing rule on all IC-CISDs: early vs late, claim '+'.
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
EARLY = pd.Timedelta("2h")


def detect_all(m1):
    b, ev = C.cisd_with_poi(m1, TF, level_rule="series_open", max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "early"]
    if ev.empty:
        return C.empty_frame(cols)
    ev = ev[ev["poi_passed"]].reset_index(drop=True)
    if ev.empty:
        return C.empty_frame(cols)
    ctx = C.htf_context(b, m1, HTF)
    x = ctx.iloc[ev["conf_pos"].to_numpy()].reset_index(drop=True)
    bull_k = ((x["p1_low"] < x["p2_low"]) & (x["p1_close"] > x["p2_low"])) | (x["p1_close"] > x["p2_high"])
    bear_k = ((x["p1_high"] > x["p2_high"]) & (x["p1_close"] < x["p2_high"])) | (x["p1_close"] < x["p2_low"])
    bull_k, bear_k = bull_k.to_numpy() & ~bear_k.to_numpy(), bear_k.to_numpy() & ~bull_k.to_numpy()
    is_bull = ev["direction"].to_numpy() == "bullish"
    aligned = np.where(is_bull, bull_k, bear_k) & x["valid"].to_numpy()
    in_k = pd.DatetimeIndex(ev["extreme_time"]) >= pd.DatetimeIndex(x["htf_start"])
    ep = ev["extreme_price"].to_numpy(dtype=float)
    wick_side = np.where(is_bull, ep < x["htf_open"].to_numpy(), ep > x["htf_open"].to_numpy())
    sel = aligned & np.asarray(in_k) & wick_side
    ev, x = ev[sel].reset_index(drop=True), x[sel].reset_index(drop=True)
    if ev.empty:
        return C.empty_frame(cols)
    out = C.to_trade_frame(ev, RR)
    age = pd.DatetimeIndex(out["decision_time"]) - pd.DatetimeIndex(x["htf_start"])
    out["early"] = np.asarray(age <= EARLY, dtype=bool)
    return out


def detect_early(m1):
    ev = detect_all(m1)
    return ev[ev["early"].astype(bool)].drop(columns=["early"]).reset_index(drop=True)


PARAMS_SOURCE = {
    "pairing": "method_spec: §1.3 favourite stack — 4H candle / 15m CISD",
    "grid4h": "session_window_fit: forex grid (default for gold)",
    "htf_direction": "method_spec: §2.3 previous-candle engine (C2 closure / close beyond prior "
                     "extreme) with phase3 §1.7 C2 rule",
    "cisd": "phase3: §1.8 series_open, 2/2, max_wait 3, min_series 1; POI gate per ic-cisd.yaml "
            "'if no FVG or high/low exists, the CISD level itself is used'",
    "wick_side": "corpus: ic-cisd.yaml 'the candle opens with a short-term bearish trend while it "
                 "forms its lower wick' => extreme beyond the 4H open",
    "early": "declared-before-run: first half (2h) of the 4H candle ('early' never quantified)",
    "rr": "corpus: ic-cisd.yaml targets '2R'",
    "max_hold": "phase3: §1.13 10 entry-TF bars",
}
OP_BASE = [
    "4H forex-grid candle k; direction from k-1/k-2 (bullish C2 or close above prior high; mirror)",
    "15m CISD (series_open, 2/2, mw3, ms1) aligned with k, POI gate passed, extreme inside k "
    "beyond k's open",
    "decide at confirm close; next M1 open; stop protected swing; 2R; 150min",
]
PARAMS = {"pairing": "4H/15m", "grid4h": "forex", "htf_direction": "prev_candle_engine",
          "cisd": "phase3+poi", "wick_side": True, "early": "2h", "rr": RR, "max_hold": MAX_HOLD}


def show(res, keys):
    for k in keys:
        print(" ", k, res.get(k))


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    keys = ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
            "exposure_bars", "ties", "ctrl_overlap")
    if "a" in which:
        ev = cl.cache_frame(f"eo01a_iccisd_early_{TF}_{HTF}", lambda: detect_early(cl.load_m1()))
        print("a events", len(ev))
        probe = cl.probe_lookahead(detect_early, ev, lookback="10D")
        res = cl.trade_test(ev, max_hold=MAX_HOLD)
        show(res, keys)
        p = cl.write_result("ic-cisd", "a", res,
                            operationalization={"rules": OP_BASE + ["keep early IC-CISDs only"],
                                                "params": PARAMS},
                            params_source=PARAMS_SOURCE, script=__file__, probe=probe)
        print("wrote", p)
    if "b" in which:
        ev = cl.cache_frame(f"eo01a_iccisd_all_{TF}_{HTF}", lambda: detect_all(cl.load_m1()))
        print("b events", len(ev), "early share", ev["early"].mean())
        probe = cl.probe_lookahead(detect_all, ev, lookback="10D")
        res = cl.gate_test(ev, "early", mask_available_at="decision_time", max_hold=MAX_HOLD)
        show(res, keys)
        p = cl.write_result("ic-cisd", "b", res,
                            operationalization={"rules": OP_BASE + ["gate: early (<=2h into the "
                                                                    "4H candle) vs late"],
                                                "params": PARAMS},
                            params_source=PARAMS_SOURCE, script=__file__, probe=probe)
        print("wrote", p)
