"""strat-two-two-reversal -> gate_test.

Source 0bH_kkG2q6s: "I'd say a one two two reversal"; practical form = "a 2-2 reversal
occurring after a liquidity run: run the structure, get the 2-2 reversal, trade it toward
the opposing highs"; "not to just take strat entries alone". measurable: "hit rate of 2-2
reversals with vs without a preceding liquidity run". claim '+': 2-2 reversals preceded
by a liquidity run beat those without.

Operationalisation (declared before the first run):
  * 15m candles (the concept's htf). STRAT classes: 2down = lower low and no higher high
    than the previous bar; 2up mirrored.
  * Bullish 2-2 reversal at bar k: bar k-1 is a 2down and bar k is a 2up. Decide at bar k's
    close; long; stop = bar k-1's low (invalidation: the reversal extreme taken out); 2R;
    hold 150 min. Bearish mirrored.
  * Gate (liquidity run): bar k-1's low is the FIRST trade below the most recent 2/2 swing
    low confirmed before bar k-1 (swing at s, confirmed at the close of s+2 <= k-2, not
    undercut between s+1 and k-2). Bearish mirrored on swing highs.
  * The 'higher-timeframe reason' condition is not applied: the source names none.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import swings22, show  # noqa: E402

CID = "strat-two-two-reversal"
TF = "15min"
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "liq_run"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    n = len(b)
    if n < 8:
        return pd.DataFrame(columns=COLS)
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    sh, sl = swings22(h, l)
    two_dn = np.r_[False, (l[1:] < l[:-1]) & (h[1:] <= h[:-1])]
    two_up = np.r_[False, (h[1:] > h[:-1]) & (l[1:] >= l[:-1])]
    bull = np.r_[False, two_dn[:-1] & two_up[1:]]
    bear = np.r_[False, two_up[:-1] & two_dn[1:]]
    sl_idx, sh_idx = np.flatnonzero(sl), np.flatnonzero(sh)
    ct = pd.DatetimeIndex(b["close_time"])
    rows = []
    for k in np.flatnonzero(bull | bear):
        if k < 4:
            continue
        up = bool(bull[k])
        idx = sl_idx if up else sh_idx
        j = np.searchsorted(idx, k - 4, "right") - 1       # swing s with s + 2 <= k - 2
        run = False
        if j >= 0:
            s = idx[j]
            if up:
                intact = l[s + 1:k - 1].min() >= l[s] if k - 1 > s + 1 else True
                run = bool(intact and l[k - 1] < l[s])
            else:
                intact = h[s + 1:k - 1].max() <= h[s] if k - 1 > s + 1 else True
                run = bool(intact and h[k - 1] > h[s])
        rows.append((k, 1 if up else -1, l[k - 1] if up else h[k - 1], run))
    if not rows:
        return pd.DataFrame(columns=COLS)
    r = pd.DataFrame(rows, columns=["k", "direction", "stop_px", "liq_run"])
    dec = ct[r["k"].to_numpy()]
    return pd.DataFrame({"decision_time": dec, "available_at": dec,
                         "direction": r["direction"].to_numpy(int),
                         "stop_px": r["stop_px"].to_numpy(float), "rr": RR,
                         "liq_run": r["liq_run"].to_numpy(bool)}).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["liq_run"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "liq_run", mask_available_at="decision_time", max_hold=MAX_HOLD)
    show(res)
    op = {"rules": [
        "15m candles; 2down = lower low without a higher high; 2up mirrored",
        "bullish 2-2 reversal: 2down then 2up; decide at the 2up close; stop = the 2down low; "
        "2R; hold 150 min (bearish mirrored)",
        "gate: the 2down bar's low is the first undercut of the most recent confirmed 2/2 "
        "swing low (bearish: swing high); gated vs complement"],
        "params": {"tf": TF, "swing": "2/2", "rr": RR, "max_hold": MAX_HOLD}}
    src = {"tf": "corpus: concept timeframes htf 15m (0bH_kkG2q6s example)",
           "swing": "declared-before-run: 'a prior high or low taken' -> the most recent "
                    "fractal 2/2 swing (same swing definition as the phase-3 CISD)",
           "rr": "phase3: 2R ('toward the opposing highs' is not mechanical)",
           "max_hold": "phase3: 10 entry-TF bars"}
    print(cl.write_result(CID, None, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Measurable 'with vs without a preceding liquidity run'. The "
                                "HTF-reason requirement and broadening-formation edge are not "
                                "applied (no mechanical definition in the source)."))
