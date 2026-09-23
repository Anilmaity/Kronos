"""oversized-fvg-handling (guest: Alex's Options) -> gate_test.

Claim tested (option A, the only handling with a mechanical rule, and the concept's first
measurable "reaction at the 50% of an oversized gap vs at its edge"): when a fair value gap
is oversized for the execution timeframe, do not enter at its edge; use its 50% mark.

Reading (declared before the run):
  * Execution TF 5m (first of the ltf list), three-bar FVGs stamped at the third bar's close.
  * Oversized: gap size >= 1.0 x ATR(20) of the 5m bars (true range, trailing 20 bars
    through the third bar) — 'big' is never quantified by the guest.
  * Trade with the gap (bullish gap -> long on the retrace). Search 48 bars (4h) after the
    third bar's close.
  * Edge arm: limit at the near edge (first M1 touch of the gap's top for a bullish gap).
    50% arm: limit at the gap's midpoint (first M1 touch), same gap.
  * Both arms: stop at the gap's far edge (the stated invalidation: price through the far
    side), target 2R, max_hold 50min; a touch minute that also trades through the stop is
    not entered.
  * gate column `ce` marks the 50% entries; claim '+' = 50% entries beat edge entries on
    control-adjusted R. cluster = gap id.
Options B-D (internal breaker, body-redrawn gap, stand aside) are alternatives with no
selection rule; they are not tested here.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import fair_value_gaps

TF = "5min"
ATR_N = 20
SIZE_ATR = 1.0
WINDOW = pd.Timedelta("4h")
RR = 2.0
MAX_HOLD = "50min"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "ce", "gap_id"]
    b = cl.build_bars(m1, TF)
    if len(b) < ATR_N + 3:
        return pd.DataFrame(columns=cols)
    f = fair_value_gaps(b[["open", "high", "low", "close"]])
    pc = b["close"].shift(1)
    tr = np.maximum(b["high"] - b["low"],
                    np.maximum((b["high"] - pc).abs(), (b["low"] - pc).abs()))
    atr = tr.rolling(ATR_N, min_periods=ATR_N).mean().to_numpy()
    big = (f["bullish_fvg"] | f["bearish_fvg"]).to_numpy() & (f["gap_size"].to_numpy() >= SIZE_ATR * atr)
    mt = m1.index.values
    MH, ML = m1["high"].to_numpy(), m1["low"].to_numpy()
    ct = b["close_time"].values
    gl, gh = f["gap_low"].to_numpy(), f["gap_high"].to_numpy()
    isbull = f["bullish_fvg"].to_numpy()
    out = []
    for i in np.flatnonzero(big):
        bull = bool(isbull[i])
        a = np.searchsorted(mt, ct[i], side="left")
        e = np.searchsorted(mt, ct[i] + WINDOW.to_timedelta64(), side="left")
        if a >= e:
            continue
        hh, ll = MH[a:e], ML[a:e]
        edge = gh[i] if bull else gl[i]
        mid = (gh[i] + gl[i]) / 2.0
        stop = gl[i] if bull else gh[i]
        gid = f"{int(ct[i].astype('int64'))}"
        beyond = (ll < stop) if bull else (hh > stop)
        for is_ce, px in ((False, edge), (True, mid)):
            touch = (ll <= px) if bull else (hh >= px)
            if not touch.any():
                continue
            k = int(np.argmax(touch))
            if beyond[:k + 1].any():
                continue
            dt = pd.Timestamp(mt[a + k]).tz_localize("UTC") + pd.Timedelta("1min")
            out.append((dt, 1 if bull else -1, stop, is_ce, gid))
    if not out:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "ce", "gap_id"])
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    ev = ev.sort_values(["decision_time", "gap_id", "ce"]).reset_index(drop=True)
    return ev[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"bigfvg_{TF}_atr{ATR_N}x{SIZE_ATR}_4h", lambda: detect(cl.load_m1()))
    print(len(ev), ev.ce.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "ce", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       cluster="gap_id")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "5m three-bar FVGs; oversized = gap >= 1.0 x ATR(20) of 5m, known at the third bar's close",
        "trade with the gap on the retrace within 4h",
        "edge arm: limit at the near edge; 50% arm: limit at the gap midpoint (same gaps)",
        "stop at the far edge; 2R; max_hold 50min; touch minute through the stop skipped",
        "gate_test: 50% rows vs edge rows, control-adjusted, clustered by gap"],
        "params": {"tf": TF, "atr_n": ATR_N, "size_atr": SIZE_ATR, "window": "4h", "rr": RR,
                   "max_hold": MAX_HOLD}}
    src = {"tf": "declared-before-run: 5m, first of the concept's ltf list (5m/1m)",
           "atr_n": "declared-before-run: ATR(20), the threshold_fits trailing-window convention",
           "size_atr": "declared-before-run: 'big' unquantified; >= 1 ATR of the execution TF",
           "window": "declared-before-run: 48 execution bars",
           "rr": "declared-before-run: no target stated; 2R",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result("oversized-fvg-handling", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Option A (50% of the oversized gap) vs the edge entry he warns against; options B-D untested (no selection rule).")
    print(p)
