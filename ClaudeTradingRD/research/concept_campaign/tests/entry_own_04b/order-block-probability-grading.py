"""order-block-probability-grading — gate_test.

Concept (Y8DkNYhq0X0, "Orderblocks Simplified"): order blocks with large bodies and small
wicks are HIGH probability (use the candle's opening price); small-body/large-wick blocks are
LOW probability. Measurable: "reaction rate of large-body/small-wick blocks vs
small-body/large-wick blocks".

Test: baseline book = the first return of price to every 1h CISD order block's opening price
(limit-style: decide at the close of the first M1 bar trading into the level, enter next M1
open), stop at the protected swing, 2R. Gate = the block candle is high-probability:
opposing_run / body <= 1.0 (threshold_fits small-wick default, grade A), where the block
candle is the first candle of the opposing series (the one whose open is the level) and its
opposing run is open -> the extreme against its own close direction.
claim '+': high-probability blocks beat low-probability blocks, control-adjusted.

All parameters are declared here before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

TF = "1h"
MAX_WAIT = 3
SWING = 2
WICK_CUT = 1.0
RETURN_BARS = 10       # the limit rests for 10 1h bars after the CISD close
RR = 2.0
MAX_HOLD = "10h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "high_prob",
            "wick_ratio", "level"]
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=SWING, right=SWING, max_wait=MAX_WAIT, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    ss = b.loc[ev["series_start"]]
    o, h, l, c = (ss[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    bull = (ev["direction"] == "bullish").to_numpy()
    body = np.abs(c - o)
    orun = np.where(bull, h - o, o - l)          # down-close candle: open->high; up: open->low
    ratio = np.where(body > 0, orun / np.where(body > 0, body, 1), np.inf)
    lvl = ev["level"].to_numpy(float)
    ps = ev["protected_swing"].to_numpy(float)
    start = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    until = start + pd.Timedelta(hours=RETURN_BARS)
    mt = m1.index.values
    ML, MH = m1["low"].to_numpy(), m1["high"].to_numpy()
    i0 = np.searchsorted(mt, start.tz_convert("UTC").as_unit("ns").values.astype(mt.dtype))
    i1 = np.searchsorted(mt, until.tz_convert("UTC").as_unit("ns").values.astype(mt.dtype))
    rows = []
    for k in range(len(ev)):
        a, z = i0[k], min(i1[k], len(mt))
        if a >= z:
            continue
        if bull[k]:
            hit = np.flatnonzero(ML[a:z] <= lvl[k])
        else:
            hit = np.flatnonzero(MH[a:z] >= lvl[k])
        if len(hit) == 0:
            continue
        j = a + hit[0]
        # a fill minute that also trades through the protected swing leaves no valid entry
        if (bull[k] and ML[j] <= ps[k]) or ((not bull[k]) and MH[j] >= ps[k]):
            continue
        t = pd.Timestamp(mt[j]).tz_localize("UTC") + pd.Timedelta(minutes=1)
        if t > until[k]:
            continue
        rows.append({"decision_time": t, "available_at": t,
                     "direction": 1 if bull[k] else -1, "stop_px": ps[k], "rr": RR,
                     "high_prob": bool(ratio[k] <= WICK_CUT),
                     "wick_ratio": float(min(ratio[k], 1e6)), "level": lvl[k]})
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows).sort_values("decision_time", kind="stable").reset_index(drop=True)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"]).as_unit("ns")
    out["available_at"] = out["decision_time"]
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"obgrade_{TF}_mw{MAX_WAIT}_ret{RETURN_BARS}_cut{WICK_CUT}",
                        lambda: detect(cl.load_m1()))
    print(len(ev), ev["high_prob"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "high_prob", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "blocks: 1h CISD (series_open, 2/2 swings, close within 3 bars); block candle = first "
        "candle of the opposing series; level = its opening price",
        "entry: first M1 bar within 10h after the CISD close that trades into the level; decide "
        "at that M1 close, enter next M1 open (limit approximation); skipped if that same "
        "minute also traded through the protected swing",
        "stop = protected swing; target 2R; max hold 10h",
        "gate high_prob: block candle opposing_run/body <= 1.0 (opposing run = open to the "
        "extreme against the candle's close direction); complement = low probability"],
        "params": {"tf": TF, "max_wait": MAX_WAIT, "swing": SWING, "wick_cut": WICK_CUT,
                   "return_bars": RETURN_BARS, "rr": RR, "max_hold": MAX_HOLD}}
    src = {"tf": "corpus: concept timeframes htf 1D/1H (blocks on the hourly)",
           "max_wait": "phase3: locked CISD config", "swing": "phase3: locked 2/2 swing",
           "wick_cut": "threshold_fits: small wick opposing_run/body <= 1.0 (grade A default)",
           "return_bars": "declared-before-run: limit rests 10 entry-TF bars",
           "rr": "method_spec: §5.3 2R floor",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result("order-block-probability-grading", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Low-probability usage restriction (established trend + sole "
                              "opposing candle) not applied: the gate compares the two shape "
                              "classes on one entry rule, as the concept's measurable asks. "
                              "Both classes enter at the opening price.")
    print(p)
