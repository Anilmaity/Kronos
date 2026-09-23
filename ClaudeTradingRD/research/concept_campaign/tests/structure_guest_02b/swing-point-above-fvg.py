"""swing-point-above-fvg (guest: DTR) -> gate_test.

Claim: an hourly swing low sitting just above an hourly bullish FVG (mirrored: swing high
just below a bearish FVG) is a favoured formation - price sweeps the swing point's
liquidity and the gap, then reacts. Measurable named in the concept: "reaction rate when a
swing point and an FVG are adjacent versus when either is isolated". claim '+'.

Baseline book (declared before the run): every 1h three-bar FVG (UTC-aligned 1h bars,
stamped at the third bar's close). Trade WITH the gap on the first M1 touch of its near
edge within 5 days (bullish gap: first M1 low <= gap_high -> long). Decision = touch minute
+ 1 min (entry next M1 open). Stop = the gap's far edge (the invalidation: price trades
through the gap). Target 2R, max_hold 10h. A touch minute that also trades through the far
edge is not entered.
Gate `adjacent`: a 2/2 fractal 1h swing low formed after the gap's third bar, confirmed
(confirming bar closed) before the touch, with its low in (gap_high, gap_high + 0.5 x
ATR(20) 1h] - i.e. "just above" the gap, and necessarily swept by the touch. Mirrored for
bearish gaps.
The concept's entry (a unicorn on the paired LTF) and target (nearest session level) are
not modelled; the gate isolates the formation itself.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import fair_value_gaps, swing_points

TF = "1h"
ADJ_ATR = 0.5
ATR_N = 20
WINDOW = pd.Timedelta("5D")
RR = 2.0
MAX_HOLD = "10h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "adjacent"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    b = b[b["n_m1"] > 0]
    if len(b) < ATR_N + 5:
        return pd.DataFrame(columns=COLS)
    ohlc = b[["open", "high", "low", "close"]]
    f = fair_value_gaps(ohlc)
    sp = swing_points(ohlc, 2, 2)
    pc = b["close"].shift(1)
    tr = np.maximum(b["high"] - b["low"],
                    np.maximum((b["high"] - pc).abs(), (b["low"] - pc).abs()))
    atr = tr.rolling(ATR_N, min_periods=ATR_N).mean().to_numpy()
    ct = b["close_time"].values
    n = len(b)
    pos = np.arange(n)
    # swing confirmation known at the close of the confirming bar (index + 2)
    conf_close = np.full(n, np.datetime64("NaT", "ns"))
    okc = pos + 2 < n
    conf_close[okc] = ct[pos[okc] + 2]
    sl_idx = np.flatnonzero(sp["swing_low"].to_numpy() & okc)
    sh_idx = np.flatnonzero(sp["swing_high"].to_numpy() & okc)
    lows, highs = b["low"].to_numpy(), b["high"].to_numpy()
    mt = m1.index.values
    MH, ML = m1["high"].to_numpy(), m1["low"].to_numpy()
    gl, gh = f["gap_low"].to_numpy(), f["gap_high"].to_numpy()
    isbull, isbear = f["bullish_fvg"].to_numpy(), f["bearish_fvg"].to_numpy()
    out = []
    for i in np.flatnonzero((isbull | isbear) & np.isfinite(atr)):
        bull = bool(isbull[i])
        a = np.searchsorted(mt, ct[i], side="left")
        e = np.searchsorted(mt, ct[i] + WINDOW.to_timedelta64(), side="left")
        if a >= e:
            continue
        if bull:
            touch = ML[a:e] <= gh[i]
        else:
            touch = MH[a:e] >= gl[i]
        if not touch.any():
            continue
        k = int(np.argmax(touch))
        if (ML[a + k] < gl[i]) if bull else (MH[a + k] > gh[i]):
            continue
        tt = mt[a + k]
        dt = tt + np.timedelta64(1, "m")
        if bull:
            cand = sl_idx[(sl_idx > i)]
            cand = cand[conf_close[cand] <= tt]
            adj = bool(((lows[cand] > gh[i]) & (lows[cand] <= gh[i] + ADJ_ATR * atr[i])).any())
            stop = gl[i]
        else:
            cand = sh_idx[(sh_idx > i)]
            cand = cand[conf_close[cand] <= tt]
            adj = bool(((highs[cand] < gl[i]) & (highs[cand] >= gl[i] - ADJ_ATR * atr[i])).any())
            stop = gh[i]
        out.append((dt, 1 if bull else -1, stop, adj))
    if not out:
        return pd.DataFrame(columns=COLS)
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "adjacent"])
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"]).tz_localize("UTC") \
        if pd.DatetimeIndex(ev["decision_time"]).tz is None else ev["decision_time"]
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    ev = ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)
    return ev[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"spafvg_{TF}_adj{ADJ_ATR}_atr{ATR_N}_5D", lambda: detect(cl.load_m1()))
    print(len(ev), ev.adjacent.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="12D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "adjacent", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "baseline: every 1h 3-bar FVG, traded with the gap on the first M1 touch of its near edge within 5 days",
        "decision = touch minute + 1; stop = far edge; 2R; 10h hold; touch minute through the far edge skipped",
        "gate adjacent: 2/2 swing low formed after the gap, confirmed before the touch, low within "
        "(gap_high, gap_high + 0.5 ATR20] (mirrored for bearish)",
        "gate_test adjacent vs isolated, control-adjusted"],
        "params": {"tf": TF, "adj_atr": ADJ_ATR, "atr_n": ATR_N, "window": "5D", "rr": RR,
                   "max_hold": MAX_HOLD, "swing": "2/2"}}
    src = {"tf": "corpus: 07lOxv39LdY 'an hourly swing low sitting just above an hourly bullish FVG'",
           "adj_atr": "declared-before-run: 'just above' has no distance; within 0.5 ATR(20) of the gap edge",
           "atr_n": "declared-before-run: ATR(20), threshold_fits trailing-window convention",
           "window": "declared-before-run: first retrace within 5 days",
           "rr": "declared-before-run: stop/target not stated; far-edge stop, 2R",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "swing": "phase3: 2/2 fractal swing (locked config)"}
    p = cl.write_result("swing-point-above-fvg", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Formation tested as a gate on a first-touch FVG book; the LTF unicorn entry "
                              "and the session-level target are not modelled.")
    print(p)
