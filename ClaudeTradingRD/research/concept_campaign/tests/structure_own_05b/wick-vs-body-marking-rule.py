"""wick-vs-body-marking-rule -> gate_test.

Source dcIdzqD3kMU: body-dominant candle -> "I will focus on the entire body of the candle",
half-level = "the mean threshold or 50% of the body"; "a large Wick and smaller body I
normally focus on the wick" -> "the low as well as a 0.5 level of this Wick". measurable:
"reaction rate at the body mean threshold vs the 0.5-of-wick level, bucketed by wick/body
ratio". claim '+': entering at the level the rule PRESCRIBES for that candle beats entering
at the level it does not prescribe, on the same blocks.

Operationalisation (declared before the first run):
  * Blocks: 1h order blocks from the phase-3 CISD (series_open level, 2/2 swings,
    max_wait 3); the block candle = the last opposing-close candle of the series (bullish
    block: a down-close candle). Valid from the CISD bar's close.
  * Wick on the relevant side: bullish block close-to-low (close - low), bearish
    high-to-close; body = |close - open|. Wick dominant := wick > body (the reading the
    words support; threshold_fits crossover 1.0).
  * Two candidate levels per block: body mean threshold (open+close)/2 and 0.5 of the wick
    (close+extreme)/2. For each: first M1 touch within 24h of validity; decide at the touch
    minute's close, enter next M1 open, trade the block's direction; stop = the protected
    swing (the extreme); 2R; hold 10h. A level at/through the stop or a touch minute that
    also reaches the stop is not entered.
  * Gate: the row's level is the one the rule prescribes (body-dominant -> body MT;
    wick-dominant -> wick 0.5). Clustered by block.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from _common import m1_arrays, from_ns, ONE_MIN, show  # noqa: E402

CID = "wick-vs-body-marking-rule"
TF = "1h"
WINDOW = pd.Timedelta("24h")
RR = 2.0
MAX_HOLD = "10h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "block_id",
        "wick_dom", "is_wick_level", "rule_level"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=COLS)
    pos = {t: i for i, t in enumerate(b.index)}
    O, H, L, C = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ctn = b["close_time"].values.astype("datetime64[ns]").astype(np.int64)
    mt, MH, ML = m1_arrays(m1)
    out = []
    for r in ev.itertuples(index=False):
        bull = r.direction == "bullish"
        i = pos[r.series_end]
        j = pos[r.confirm_time]
        body = abs(C[i] - O[i])
        wick = (C[i] - L[i]) if bull else (H[i] - C[i])
        wdom = bool(wick > body)
        stop = float(r.protected_swing)
        levels = {False: (O[i] + C[i]) / 2,
                  True: (C[i] + L[i]) / 2 if bull else (C[i] + H[i]) / 2}
        a = np.searchsorted(mt, ctn[j], "left")
        e = np.searchsorted(mt, ctn[j] + WINDOW.value, "left")
        if a >= e:
            continue
        for is_w, lv in levels.items():
            if (lv <= stop) if bull else (lv >= stop):
                continue
            hit = (ML[a:e] <= lv) if bull else (MH[a:e] >= lv)
            if not hit.any():
                continue
            k = int(np.argmax(hit))
            if (ML[a + k] <= stop) if bull else (MH[a + k] >= stop):
                continue
            out.append((int(mt[a + k]), 1 if bull else -1, stop, int(ctn[j]) + (1 if bull else 0),
                        wdom, is_w))
    if not out:
        return pd.DataFrame(columns=COLS)
    o = pd.DataFrame(out, columns=["t", "direction", "stop_px", "block_id", "wick_dom",
                                   "is_wick_level"])
    dec = from_ns(o["t"].to_numpy()) + ONE_MIN
    ev2 = pd.DataFrame({"decision_time": dec, "available_at": dec,
                        "direction": o["direction"].astype(int).to_numpy(),
                        "stop_px": o["stop_px"].to_numpy(float), "rr": RR,
                        "block_id": o["block_id"].astype(np.int64).to_numpy(),
                        "wick_dom": o["wick_dom"].astype(bool).to_numpy(),
                        "is_wick_level": o["is_wick_level"].astype(bool).to_numpy()})
    ev2["rule_level"] = (ev2["wick_dom"] == ev2["is_wick_level"])
    return ev2.sort_values(["decision_time", "block_id", "is_wick_level"]) \
        .reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}_24h_rr2", lambda: detect(cl.load_m1()))
    print(len(ev), ev["rule_level"].mean(), ev["wick_dom"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "rule_level", mask_available_at="decision_time",
                       max_hold=MAX_HOLD, cluster="block_id")
    show(res)
    op = {"rules": [
        "1h order blocks from phase-3 CISD (series_open, 2/2, max_wait 3); block candle = "
        "last opposing-close candle of the series; valid from the CISD close",
        "wick dominant := relevant-side wick (bullish close-low, bearish high-close) > body",
        "levels: body mean threshold (open+close)/2 and 0.5 of the wick (close+extreme)/2",
        "each level: first M1 touch within 24h, next M1 open, block direction, stop = "
        "protected swing, 2R, hold 10h; skip if the touch minute reaches the stop",
        "gate: row's level is the rule-prescribed one; clustered by block"],
        "params": {"tf": TF, "window": "24h", "wick_cut": "wick > body", "rr": RR,
                   "max_hold": MAX_HOLD, "block_candle": "series_end"}}
    src = {"tf": "declared-before-run: 1h from the concept's htf list (1D/4H/1H), phase-3 "
                 "rung-0 blocks",
           "window": "declared-before-run: retest eligibility not stated; 24h",
           "wick_cut": "threshold_fits: wick vs body crossover 1.0 (grade A); the concept's "
                       "own ambiguity note 'wick_span > body_span is the reading the words "
                       "support'",
           "rr": "phase3: 2R primary target", "max_hold": "phase3: 10 entry-TF bars",
           "block_candle": "declared-before-run: the block's candle = the opposing candle "
                           "nearest the extreme (blocks.order_blocks series)"}
    print(cl.write_result(CID, None, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Same blocks, two candidate levels each; the rule's choice vs "
                                "the other choice. wick-dominant share and counts in stdout."))
