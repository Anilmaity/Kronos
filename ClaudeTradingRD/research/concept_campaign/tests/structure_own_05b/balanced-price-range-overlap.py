"""balanced-price-range-overlap (contested) -> reading a: trade_test; reading b: gate_test.

Claim (yOPESX2aWkI): "if you combine the two whatever one is smaller there is your BPR";
"ideally you are looking for a retracement back to this area"; "you don't want to be
longing in a premium". execution: bias = direction of the second aggressive move; entry =
retracement into the overlap; stop = beyond the extreme that formed the first gap.

Reading a (trade_test, claim '+'): the bare BPR retracement trade beats a matched random
entry.
Reading b (gate_test, claim '+'): on the reading-a book, BPRs on the correct side of
equilibrium (longs in discount, shorts in premium of the previous day's range) beat BPRs on
the wrong side.

Operationalisation (all declared before the first run):
  * 15m three-bar FVGs (detectors.primitives.fair_value_gaps), known at the third bar close.
  * BPR = a new FVG (the second, later gap) whose price range overlaps an OPPOSING FVG formed
    at most 20 bars earlier (the most recent such gap). Zone = the intersection (partial
    overlap suffices). Direction = the second gap's.
  * Stop = the extreme between the two gaps (bearish BPR: the max high from the first gap's
    first bar to the second gap's third bar; bullish mirrored) - the extreme of the first
    aggressive move.
  * Entry: first M1 touch of the zone's near edge within 24h of the second gap; decide at
    the touch minute's close, enter next M1 open; a touch minute that also trades through the
    stop is not entered. 2R target; hold 150 min.
  * Gate (b): equilibrium = midpoint of the previous trading day's range (prior_hilo 1D at
    the decision); pass = long with zone midpoint below EQ / short with zone midpoint above.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from detectors.primitives import fair_value_gaps  # noqa: E402
from _common import m1_arrays, from_ns, ONE_MIN, show  # noqa: E402

CID = "balanced-price-range-overlap"
TF = "15min"
PAIR_BARS = 20
WINDOW = pd.Timedelta("24h")
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "bpr_id",
        "zone_mid", "correct_side"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < 5:
        return pd.DataFrame(columns=COLS)
    f = fair_value_gaps(b[["open", "high", "low", "close"]])
    isbull = f["bullish_fvg"].to_numpy(bool)
    isbear = f["bearish_fvg"].to_numpy(bool)
    gl, gh = f["gap_low"].to_numpy(float), f["gap_high"].to_numpy(float)
    bh, bl = b["high"].to_numpy(float), b["low"].to_numpy(float)
    ct = b["close_time"].values.astype("datetime64[ns]").astype(np.int64)
    mt, MH, ML = m1_arrays(m1)
    W = WINDOW.value
    gaps = np.flatnonzero(isbull | isbear)
    out = []
    for jj, j in enumerate(gaps):
        bull = bool(isbull[j])
        # most recent opposing gap within PAIR_BARS whose range overlaps
        first = -1
        for i in gaps[max(0, jj - PAIR_BARS - 1):jj][::-1]:
            if j - i > PAIR_BARS:
                break
            if bool(isbull[i]) == bull:
                continue
            if min(gh[i], gh[j]) > max(gl[i], gl[j]):
                first = i
                break
        if first < 0:
            continue
        lo, hi = max(gl[first], gl[j]), min(gh[first], gh[j])
        s0 = max(first - 2, 0)
        stop = bl[s0:j + 1].min() if bull else bh[s0:j + 1].max()
        a = np.searchsorted(mt, ct[j], "left")
        e = np.searchsorted(mt, ct[j] + W, "left")
        if a >= e:
            continue
        hh, ll = MH[a:e], ML[a:e]
        touch = (ll <= hi) if bull else (hh >= lo)
        if not touch.any():
            continue
        k = int(np.argmax(touch))
        if (ll[k] <= stop) if bull else (hh[k] >= stop):
            continue
        out.append((int(mt[a + k]), 1 if bull else -1, stop, int(ct[j]), (lo + hi) / 2))
    if not out:
        return pd.DataFrame(columns=COLS)
    o = pd.DataFrame(out, columns=["t", "direction", "stop_px", "bpr_id", "zone_mid"])
    dec = from_ns(o["t"].to_numpy()) + ONE_MIN
    pd_ = cl.prior_hilo(dec, "1D", m1=m1)
    eq = ((pd_["high"] + pd_["low"]) / 2).to_numpy(float)
    ev = pd.DataFrame({"decision_time": dec, "available_at": dec,
                       "direction": o["direction"].astype(int).to_numpy(),
                       "stop_px": o["stop_px"].to_numpy(float), "rr": RR,
                       "bpr_id": o["bpr_id"].astype(np.int64).to_numpy(),
                       "zone_mid": o["zone_mid"].to_numpy(float), "eq": eq})
    ev = ev[np.isfinite(ev["eq"].to_numpy())]
    ev["correct_side"] = np.where(ev["direction"] > 0, ev["zone_mid"] < ev["eq"],
                                  ev["zone_mid"] > ev["eq"]).astype(bool)
    return ev.sort_values(["decision_time", "bpr_id"]).reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}_p{PAIR_BARS}_24h_rr2", lambda: detect(cl.load_m1()))
    print(len(ev), ev["correct_side"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    params = {"tf": TF, "pair_bars": PAIR_BARS, "window": "24h", "rr": RR,
              "max_hold": MAX_HOLD, "eq_range": "previous trading day (18:00 NY roll)"}
    src = {"tf": "declared-before-run: 15m from the concept's htf list (1D/4H/1H/15m); "
                 "fractal: true",
           "pair_bars": "declared-before-run: adjacency of the two gaps is not stated "
                        "(ambiguity); 20 bars = 5h",
           "window": "declared-before-run: eligibility of the retracement unstated; 24h",
           "rr": "phase3: 2R primary target (equal highs/lows / HTF draw not mechanical)",
           "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13)",
           "eq_range": "method_spec: 2.4 marks the previous day's EQ as the operative "
                       "equilibrium (declared-before-run for this concept)"}
    rules_a = [
        "15m three-bar FVGs known at the third bar's close",
        "BPR = a new FVG overlapping an opposing FVG formed <= 20 bars earlier; zone = "
        "intersection; direction = the later gap",
        "stop = the extreme between the two gaps (the first aggressive move's extreme)",
        "entry: first M1 touch of the zone's near edge within 24h; next M1 open; skip if "
        "the touch minute also hits the stop; 2R; hold 150 min"]
    res = cl.trade_test(ev, max_hold=MAX_HOLD, cluster="bpr_id")
    print("reading a"); show(res)
    print(cl.write_result(CID, "a", res, operationalization={"rules": rules_a,
                          "params": params}, params_source=src, script=__file__,
                          probe=probe, notes="Bare BPR retracement trade; the liquidity-raid "
                          "precondition is not applied (no mechanical POI given)."))
    resb = cl.gate_test(ev, "correct_side", mask_available_at="decision_time",
                        max_hold=MAX_HOLD, cluster="bpr_id")
    print("reading b"); show(resb)
    print(cl.write_result(CID, "b", resb, operationalization={
        "rules": rules_a + ["gate: long BPR with zone midpoint below the previous day's EQ, "
                            "short above (premium/discount rule); gated vs complement"],
        "params": params}, params_source=src, script=__file__, probe=probe,
        notes="Premium/discount rejection rule tested as a gate on the reading-a book."))
