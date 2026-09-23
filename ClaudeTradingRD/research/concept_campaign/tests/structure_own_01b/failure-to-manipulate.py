"""failure-to-manipulate — deflated to phases of price (specified).

Concept: concepts/structure/failure-to-manipulate.yaml (live_streams_04, i2HhHhWdaPQ).

"Price expands into that low. Either it expands back out, which is the reversal, or it does
not, which is a retracement or a consolidation and therefore a continuation through the
level." The actionable claim is the failure branch: no reversal -> continuation.

Operationalisation (trade_test), 1h bars:
  * target level = the previous completed trading day's low (high) — "a level (a previous
    low or high) is being used as a target"; previous-day extremes always qualify
    (method_spec §2.7 relevant level). Stub sessions (< 600 M1 bars) skipped.
  * expansion INTO it: a bearish 1h expansion event (threshold_fits §2) whose break bar
    opened above the PDL and whose 4-bar window traded to or through the PDL.
  * classification window: the 4 bars after the expansion's decision. Reversal branch =
    an opposing (bullish) expansion event decided inside that window ("expands back
    out"). Failure branch = none.
  * failure branch only: at the close of the 4th classification bar go with the original
    expansion (short), stop = the highest high from the expansion's low bar to the
    decision (the top of the retracement/consolidation), target 2R, 10h hold.
The "two correlated assets" clause is not traded: the concept does not say what the second
asset must show (its own ambiguity), so this is the single-asset reading.
All parameters declared before the first run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402

CID = "failure-to-manipulate"
KWIN = 4
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def detect(m1):
    b = cl.build_bars(m1, "1h")
    ex = C.expansions(b)
    if ex.empty:
        return C.empty_frame(COLS)
    day = cl.build_bars(m1, "1D")
    day = day[day["n_m1"] >= 600]
    dct = pd.DatetimeIndex(day["close_time"]).as_unit("ns").asi8
    dlo, dhi = day["low"].to_numpy(), day["high"].to_numpy()
    o, h, l = b["open"].to_numpy(), b["high"].to_numpy(), b["low"].to_numpy()
    st = b.index.as_unit("ns").asi8
    ct = b["close_time"].to_numpy()
    nb = len(b)
    E_dir = ex["dir"].to_numpy()
    E_brk = ex["break_pos"].to_numpy()
    E_dec = ex["dec_pos"].to_numpy()
    rows = []
    for k in range(len(ex)):
        dr, bp, dp = int(E_dir[k]), int(E_brk[k]), int(E_dec[k])
        j = np.searchsorted(dct, st[bp], side="right") - 1        # last day closed by break
        if j < 0:
            continue
        w = slice(bp, dp + 1)
        if dr == -1:
            lvl = dlo[j]
            if not (o[bp] > lvl and l[w].min() <= lvl):
                continue
        else:
            lvl = dhi[j]
            if not (o[bp] < lvl and h[w].max() >= lvl):
                continue
        end = dp + KWIN
        if end >= nb:
            continue
        # reversal branch: an opposing expansion decided inside the classification window
        opp = (E_dir == -dr) & (E_dec > dp) & (E_dec <= end) & (E_brk > bp)
        if opp.any():
            continue
        if dr == -1:
            xb = bp + int(np.argmin(l[w]))
            stop = h[xb:end + 1].max()
        else:
            xb = bp + int(np.argmax(h[w]))
            stop = l[xb:end + 1].min()
        rows.append({"decision_time": ct[end], "available_at": ct[end], "direction": dr,
                     "stop_px": float(stop), "rr": 2.0})
    if not rows:
        return C.empty_frame(COLS)
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = pd.DatetimeIndex(out["available_at"])
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)[COLS]


EXP_SRC = ("threshold_fits: §2 displacement=aggressive, close-beyond gate (grade A) + N=4 "
           "window r>=1.5, d>=0.65 vs the pre-break 4-bar range (grade B); 2/2 fractal swings")


def run():
    ev = cl.cache_frame("so01b_ftm_1h_pdl", lambda: detect(cl.load_m1()))
    print("events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.trade_test(ev, max_hold="10h", hold_basis="bars", ctrl_tod_tol_min=30)
    C.show(res)
    op = {"rules": [
        "1h UTC bars; level = previous completed trading day low/high (18:00 NY roll, "
        "sessions >= 600 M1 bars)",
        "bearish 1h expansion event (close beyond 2/2 swing, 4-bar window range/pre-range "
        ">= 1.5 and distance/pre-range >= 0.65) whose break bar opened above the PDL and "
        "whose window traded to/through it (mirror: bullish into PDH)",
        "reversal branch = opposing expansion decided within the next 4 bars -> skipped; "
        "failure branch = none -> decide at the close of the 4th bar",
        "trade the original direction: next M1 open, stop = extreme of the retracement "
        "since the expansion's low bar, 2R, 10h trading time; control NY clock +/-30 min"],
        "params": {"tf": "1h", "level": "PDL/PDH", "min_day_m1": 600, "exp_n": 4,
                   "exp_r": 1.5, "exp_d": 0.65, "class_window": KWIN, "rr": 2.0,
                   "max_hold": "10h", "hold_basis": "bars", "ctrl_tod_tol_min": 30}}
    src = {"tf": "declared-before-run: 1h (concept ltf list 1H)",
           "level": "method_spec: §2.7 'previous day and previous week extremes always qualify'",
           "min_day_m1": "declared-before-run: trap 6 stub sessions skipped",
           "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
           "class_window": "declared-before-run: one displacement window (N=4) to see "
                           "whether price expands back out",
           "rr": "phase3: §1.12 2R",
           "max_hold": "phase3: §1.13 10 entry-TF bars",
           "hold_basis": "declared-before-run: trading time (trap 7)",
           "ctrl_tod_tol_min": "declared-before-run: trap 9, not a timing concept",
           "branch": "corpus: i2HhHhWdaPQ 'It's really just phases of price.'"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Single-asset reading; the correlated-asset clause names no "
                              "condition and is not traded.")
    print("wrote", p)


if __name__ == "__main__":
    run()
