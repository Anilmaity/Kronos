"""failure-swing-draw (guest: AP, gjoRPszj-Qk) -> trade_test.

Reading (declared before the run), bearish case (bullish mirrored):
  * Working TF 15m (listed LTF, fractal: true), fractal 2/2 swings.
  * SH1 = the most recent confirmed swing high before SH2; L = the lowest low strictly
    between them ('the lows that produced that failure swing'); no high between them
    exceeds SH1.
  * Failure swing high SH2 = the next fractal swing high with SH1 > SH2 and SH2 having
    retraced at least 70% of the SH1 -> L leg ('price approaches the prior high and turns
    without exceeding it'; the closeness tolerance is not stated, 0.70 is the deepest of
    the speaker's own 30/50/70 retracement set).
  * Confirmation (the internal flip, 'a close above then a close below'): the first 15m
    bar i >= j+2 (swing confirmed) whose CLOSE is below the low of the SH2 bar, within 8
    bars of SH2, with no high above SH2 and no low at/below L in between.
  * Trade: short at that close (harness: next M1 open), stop = SH2 (the failure-swing
    extreme), target = L (the draw).  max_hold 24h.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_guest_01b")
from common01b import cl, bars_arr, swing_flags, to_utc  # noqa: E402

TF = "15min"
SWING = (2, 2)
RETR = 0.70
MAX_WAIT = 8
MAX_HOLD = "24h"


def _side(h, l, c, sh, right, sign):
    """sign=+1: failure swing HIGH -> short.  For sign=-1 pass negated arrays."""
    rows = []
    idx = np.flatnonzero(sh)
    n = len(h)
    for p in range(1, len(idx)):
        a, j = idx[p - 1], idx[p]
        if j - a < 2:
            continue
        sh1, sh2 = h[a], h[j]
        if not sh2 < sh1:
            continue
        mid_l = l[a + 1:j]
        L = mid_l.min()
        if h[a + 1:j].max() > sh1:
            continue
        if sh2 < L + RETR * (sh1 - L):
            continue
        # confirmation scan
        lo_j = l[j]
        for i in range(j + 1, min(j + MAX_WAIT, n - 1) + 1):
            if h[i] > sh2 or l[i] <= L:
                break
            if i >= j + right and c[i] < lo_j:
                if c[i] > L:
                    rows.append((i, sh2, L, j))
                break
    return rows


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bars_arr(cl.build_bars(m1, TF))
    h, l, c = b["h"], b["l"], b["c"]
    sh, sl = swing_flags(h, l, *SWING)
    right = SWING[1]
    out = []
    for i, stop, tgt, j in _side(h, l, c, sh, right, 1):
        out.append((i, -1, stop, tgt, j))
    for i, stop, tgt, j in _side(-l, -h, -c, sl, right, -1):
        out.append((i, 1, -stop, -tgt, j))
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "swing_t"]
    if not out:
        return pd.DataFrame(columns=cols)
    f = pd.DataFrame(out, columns=["bar", "direction", "stop_px", "target_px", "j"])
    f["decision_time"] = to_utc(b["close_t"][f["bar"].to_numpy()])
    f["available_at"] = f["decision_time"]
    f["swing_t"] = to_utc(b["start"][f["j"].to_numpy()])
    f = f.sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)
    return f[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"fsd_{TF}_{SWING}_{RETR}_{MAX_WAIT}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "ties", "ctrl_overlap", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "15m bars, fractal 2/2 swings.",
        "Failure swing high SH2 = fractal swing high below the previous swing high SH1, with no high between them above SH1, retracing >= 70% of the SH1 -> L leg (L = lowest low between them). Mirror for lows.",
        "Confirm: first bar >= SH2+2 bars, within 8 bars, closing below the SH2 bar's low, with no new high above SH2 and L not yet reached.",
        "Short at the confirming close; stop SH2; target L (the draw); max_hold 24h."],
        "params": {"tf": TF, "swing_left_right": SWING, "min_retrace": RETR, "max_wait_bars": MAX_WAIT,
                   "max_hold": MAX_HOLD}}
    ps = {"tf": "declared-before-run: 15m (listed LTF; fractal concept)",
          "swing_left_right": "declared-before-run: fractal 2/2",
          "min_retrace": "corpus: gjoRPszj-Qk retracement set '30 / 50 / 70' (deepest used as the approach tolerance; declared-before-run)",
          "max_wait_bars": "declared-before-run: 8 bars (2h) for the internal flip",
          "max_hold": "declared-before-run: 24h"}
    notes = "Target/stop are structural (L and SH2); the matched control holds both distances."
    print(cl.write_result("failure-swing-draw", None, res, operationalization=op, params_source=ps,
                          script=__file__, probe=probe, notes=notes))
