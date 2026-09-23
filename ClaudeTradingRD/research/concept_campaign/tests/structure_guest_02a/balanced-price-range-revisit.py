"""balanced-price-range-revisit (guest: Ben) -> gate_test.

Claim (yRmKkR4CojU): a BPR = a fair value gap that has ALREADY been filled and is then
revisited; "bprs ... tend to be more sensitive than fair value gaps" -> he ranks a
filled-and-revisited gap above an untouched one. Tested as: on the same population of
15m three-bar FVGs, is the revisit of a filled gap a better entry than the first touch of
the untouched gap? claim '+' (BPR rows beat plain-FVG rows on control-adjusted R).

Reading (all declared before the first run):
  * 15m three-bar FVGs (detectors.primitives.fair_value_gaps), known at the third bar's close.
  * Eligibility window 24h from the gap's formation (how long a filled gap stays eligible
    is not stated).
  * Plain-FVG arm (mask False): first M1 touch of the gap's near edge (bullish gap: its
    top), trade WITH the gap, stop at the far edge ("beyond the band"), 2R. A touch minute
    that also trades through the far edge is not entered.
  * BPR arm (mask True): the gap is filled = a 15m bar CLOSES beyond its far edge (price has
    traded fully through and is on the far side). The revisit = first M1 touch back at the
    band (bullish gap: its bottom, from below) after that close. Trade in the direction of
    the FILLING leg (yaml execution.bias; for a bullish gap: short), stop beyond the band
    (the gap's top), 2R. A revisit minute that trades through the whole band is not entered.
  * Entry at the next M1 open after the touch minute; hold 10 entry-TF bars = 150 min.
  * cluster = gap id (both arms can come from one gap).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from detectors.primitives import fair_value_gaps  # noqa: E402
from _common import m1_arrays, from_ns, ONE_MIN  # noqa: E402

CID = "balanced-price-range-revisit"
TF = "15min"
WINDOW = pd.Timedelta("24h")
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "is_bpr", "gap_id",
        "gap_time"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < 5:
        return pd.DataFrame(columns=COLS)
    f = fair_value_gaps(b[["open", "high", "low", "close"]])
    isbull = f["bullish_fvg"].to_numpy(bool)
    isbear = f["bearish_fvg"].to_numpy(bool)
    gl, gh = f["gap_low"].to_numpy(float), f["gap_high"].to_numpy(float)
    ct = b["close_time"].values.astype("datetime64[ns]").astype(np.int64)
    bc = b["close"].to_numpy(float)
    mt, MH, ML = m1_arrays(m1)
    W = WINDOW.value
    out = []
    for i in np.flatnonzero(isbull | isbear):
        bull = bool(isbull[i])
        lo, hi = gl[i], gh[i]
        a = np.searchsorted(mt, ct[i], "left")
        e = np.searchsorted(mt, ct[i] + W, "left")
        if a >= e:
            continue
        hh, ll = MH[a:e], ML[a:e]
        gid = int(ct[i])
        # plain arm: first touch of the near edge, trade with the gap
        near, far = (hi, lo) if bull else (lo, hi)
        touch = (ll <= near) if bull else (hh >= near)
        if touch.any():
            k = int(np.argmax(touch))
            through = (ll[k] < far) if bull else (hh[k] > far)
            if not through:
                out.append((int(mt[a + k]), 1 if bull else -1, far, False, gid, int(ct[i])))
        # BPR arm: a 15m close beyond the far edge, then a revisit of the band
        kb = np.searchsorted(ct, ct[i], "right")
        ke = np.searchsorted(ct, ct[i] + W, "right")
        seg = bc[kb:ke]
        fill = (seg < lo) if bull else (seg > hi)
        if not fill.any():
            continue
        kf = kb + int(np.argmax(fill))
        a2 = np.searchsorted(mt, ct[kf], "left")
        if a2 >= e:
            continue
        hh2, ll2 = MH[a2:e], ML[a2:e]
        # bullish gap filled from above: price below lo, revisit = high >= lo -> short, stop hi
        rv = (hh2 >= lo) if bull else (ll2 <= hi)
        if not rv.any():
            continue
        k2 = int(np.argmax(rv))
        through = (hh2[k2] > hi) if bull else (ll2[k2] < lo)
        if through:
            continue
        out.append((int(mt[a2 + k2]), -1 if bull else 1, hi if bull else lo, True, gid,
                    int(ct[i])))
    if not out:
        return pd.DataFrame(columns=COLS)
    o = pd.DataFrame(out, columns=["t", "direction", "stop_px", "is_bpr", "gap_id", "gap_t"])
    dec = from_ns(o["t"].to_numpy()) + ONE_MIN
    ev = pd.DataFrame({"decision_time": dec, "available_at": dec,
                       "direction": o["direction"].astype(int).to_numpy(),
                       "stop_px": o["stop_px"].to_numpy(float), "rr": RR,
                       "is_bpr": o["is_bpr"].astype(bool).to_numpy(),
                       "gap_id": o["gap_id"].astype(np.int64).to_numpy(),
                       "gap_time": from_ns(o["gap_t"].to_numpy())})
    return ev.sort_values(["decision_time", "gap_id", "is_bpr"]).reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}_24h_rr2", lambda: detect(cl.load_m1()))
    print(len(ev), ev["is_bpr"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "is_bpr", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       cluster="gap_id")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "complement"):
        print(k, res.get(k))
    op = {"rules": [
        "15m three-bar FVGs, known at the third bar's close; eligible for 24h",
        "plain arm: first M1 touch of the near edge, trade with the gap, stop far edge, 2R",
        "BPR arm: gap filled = a 15m close beyond the far edge; revisit = first M1 touch back "
        "at the band after that close; trade in the filling leg's direction; stop beyond the "
        "band (the other edge); 2R",
        "touch minutes that trade through the stop edge are skipped; entry next M1 open; "
        "hold 150 min",
        "gate_test: BPR rows vs plain rows, control-adjusted, clustered by gap"],
        "params": {"tf": TF, "window": "24h", "rr": RR, "max_hold": MAX_HOLD,
                   "fill": "15m close beyond far edge"}}
    src = {"tf": "declared-before-run: 15m from the concept's ltf list (1H/15m/5m/1m); "
                 "fractal: true",
           "window": "declared-before-run: eligibility unstated ('How long a filled gap stays "
                     "eligible is not stated'); 24h = 96 entry bars",
           "rr": "declared-before-run: target 'the next step of the PD array ladder' is not "
                 "mechanical; 2R (phase3 primary target)",
           "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13)",
           "fill": "corpus: yRmKkR4CojU 'fegs that have already been filled that get revisited'; "
                   "a close beyond the far edge = filled and left (declared-before-run)"}
    notes = ("Direction of the BPR trade = the filling leg (yaml execution.bias 'direction of "
             "the leg that ... filled the gap'). Comparison is his ranking claim: BPR revisit "
             "vs untouched FVG first touch on the same gap population.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
