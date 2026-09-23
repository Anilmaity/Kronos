"""manipulation-first-heuristic — Find the manipulation first, then derive the range. Own voice.

Operationalisation (`underspecified`; 'aggressive' taken from threshold_fits), 15m bars:
  * accumulation range = high/low of the RANGE_N bars before the break bar i;
  * manipulation = bar i is the FIRST bar to trade beyond that range (bearish case: above
    the range high), and within N_WIN=4 bars from the break (i..i+3) a bar j CLOSES back
    inside the range — "trades sharply beyond ... followed by an equally sharp return";
  * aggressive (threshold_fits displacement magnitude, N=4): over bars i..j, the excursion
    beyond the range edge >= 0.65 x the pre-break 4-bar range AND the i..j range >= 1.5 x
    the pre-break 4-bar range;
  * distribution expected on the opposite side: trade at bar j's close toward the opposite
    range extreme (target), stop beyond the excursion extreme, exit after 10 bars.
Test: trade_test vs matched random entry (same stop and target distances), claim '+'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                            # noqa: E402

CID = "manipulation-first-heuristic"
TF = "15min"
RANGE_N = 20
N_WIN = 4
R_MULT = 1.5
D_MULT = 0.65
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < RANGE_N + N_WIN + 2:
        return pd.DataFrame(columns=COLS)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    rh = pd.Series(h).rolling(RANGE_N, min_periods=RANGE_N).max().shift(1).to_numpy()
    rl = pd.Series(l).rolling(RANGE_N, min_periods=RANGE_N).min().shift(1).to_numpy()
    p4h = pd.Series(h).rolling(N_WIN, min_periods=N_WIN).max().shift(1).to_numpy()
    p4l = pd.Series(l).rolling(N_WIN, min_periods=N_WIN).min().shift(1).to_numpy()
    pre = p4h - p4l
    n = len(b)
    rows = []
    for i in range(RANGE_N + 1, n):
        if not (np.isfinite(rh[i]) and np.isfinite(pre[i]) and pre[i] > 0):
            continue
        for side in (-1, 1):                        # -1: buyside run then short
            if side < 0:
                out_i = h[i] > rh[i]
                first = not (h[i - 1] > rh[i - 1]) if np.isfinite(rh[i - 1]) else True
            else:
                out_i = l[i] < rl[i]
                first = not (l[i - 1] < rl[i - 1]) if np.isfinite(rl[i - 1]) else True
            if not (out_i and first):
                continue
            edge = rh[i] if side < 0 else rl[i]
            opp = rl[i] if side < 0 else rh[i]
            for j in range(i, min(n, i + N_WIN)):
                back = c[j] < edge if side < 0 else c[j] > edge
                if not back:
                    continue
                hi, lo = h[i:j + 1].max(), l[i:j + 1].min()
                ext = hi if side < 0 else lo
                dist = (hi - edge) if side < 0 else (edge - lo)
                if dist >= D_MULT * pre[i] and (hi - lo) >= R_MULT * pre[i]:
                    rows.append({"decision_time": ct[j], "available_at": ct[j],
                                 "direction": side, "stop_px": float(ext),
                                 "target_px": float(opp)})
                break
    out = pd.DataFrame(rows, columns=COLS)
    return out.drop_duplicates(["decision_time", "direction"]).reset_index(drop=True)


OP = {"rules": [
    "15m bars; accumulation range = high/low of the 20 bars before the break bar",
    "manipulation = first bar beyond the range, then a close back inside within 4 bars of "
    "the break (the break bar itself may close back)",
    "aggressive = excursion beyond the edge >= 0.65 x and break-window range >= 1.5 x the "
    "4-bar pre-break range (threshold_fits displacement magnitude)",
    "trade toward the opposite range extreme at the close back inside; stop at the "
    "excursion extreme; exit after 150 min"],
    "params": {"tf": TF, "range_n": RANGE_N, "n_win": N_WIN, "r": R_MULT, "d": D_MULT,
               "max_hold": MAX_HOLD}}
SRC = {"tf": "corpus: TCFvsZeYvV8 — ltf 15m/5m/1m, fractal; phase3: 15m primary entry TF",
       "range_n": "declared-before-run: 'how far left to look' is not stated; 20 bars",
       "n_win": "threshold_fits: displacement magnitude N=4 (corpus 1oco9lesido 'these four "
                "candles')",
       "r": "threshold_fits: displacement magnitude r=1.5",
       "d": "threshold_fits: displacement magnitude d=0.65",
       "max_hold": "phase3: 10 entry-TF bars (§1.13)"}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "dropped"):
        print(k, res.get(k))
    p = cl.write_result(CID, None, res, operationalization=OP, params_source=SRC,
                        script=__file__, probe=probe,
                        notes="'Aggressive' is undefined in the corpus; the threshold_fits "
                              "displacement-magnitude defaults (N=4, r=1.5, d=0.65) are used.")
    print(p)
