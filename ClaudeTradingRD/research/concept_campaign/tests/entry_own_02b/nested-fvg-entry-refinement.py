"""nested-fvg-entry-refinement — batch entry_own_02b.

ivirRu3fc4o: mark the 15m FVG inside the OTE of a displacement range, drop to the 5m
gap inside it, then drop again and look LEFT for a gap nested between the two; enter
at that innermost gap ("little to no drawdown").

The 15-second chart is not in the data (M1 is the finest); the corpus says the
15m/5m/15s ladder is "the example, not a stated ladder", so the ladder here is
15m / 5m / 1m.

Book (union, same setups): 15m displacement legs as in optimal-trade-entry (2/2
swings, close-through break, anchor -> first swing extreme after the break). A setup
needs a same-direction 15m FVG formed inside the leg overlapping the 0.62-0.79 band.
  arm "15m":    limit at that 15m gap's near edge.
  arm "nested": when a same-direction 5m FVG inside the leg overlaps the 15m gap AND a
                same-direction 1m FVG inside the leg overlaps that overlap, limit at the
                near edge of the three-way intersection.
Both: stop = leg anchor, target = leg extreme, fill = first M1 touch within 20 x 15m
bars of arming, before a new leg extreme; 5h hold. gate_test mask = nested, claim '+'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                    # noqa: E402
from _common import (M1, bars_with_swings, displacement_legs, first_touch,  # noqa: E402
                     fvg_arrays, to_ts, ns, ONE_MIN)

TF = "15min"
BAND = (0.62, 0.79)
WAIT_BARS = 20
MAX_HOLD = "5h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "nested"]


def _pick(bull, glo, ghi, lo_lim, hi_lim, up):
    """Among gaps (arrays already restricted to the leg & polarity), those overlapping
    [lo_lim, hi_lim]; return the intersection of the one reached first (highest near edge
    for a long) or None."""
    ok = bull & (ghi >= lo_lim) & (glo <= hi_lim)
    if not ok.any():
        return None
    lo = np.maximum(glo[ok], lo_lim)
    hi = np.minimum(ghi[ok], hi_lim)
    k = int(np.argmax(hi)) if up else int(np.argmin(lo))
    return float(lo[k]), float(hi[k])


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 500:
        return pd.DataFrame(columns=COLS)
    b, d = bars_with_swings(m1, TF, 2, 2)
    legs = displacement_legs(d, right=2)
    b15, s15, g15lo, g15hi = fvg_arrays(d)
    t15 = d["ct"]                       # 15m gap known at its 3rd bar close
    b5 = cl.build_bars(m1, "5min")
    d5 = {"h": b5["high"].to_numpy(float), "l": b5["low"].to_numpy(float)}
    u5, dn5, g5lo, g5hi = fvg_arrays(d5)
    t5 = ns(b5["close_time"])
    s5 = ns(b5.index)
    m = M1(m1)
    d1 = {"h": m.h, "l": m.l}
    u1, dn1, g1lo, g1hi = fvg_arrays(d1)
    t1 = m.t + ONE_MIN
    s1 = m.t
    bar_ns = np.int64(15) * ONE_MIN
    rows = []
    for r in legs.itertuples(index=False):
        up = r.dir == 1
        L, H = float(r.L), float(r.H)
        R = (H - L) if up else (L - H)
        if not R > 0:
            continue
        band_hi = (H - BAND[0] * R) if up else (H + BAND[1] * R)
        band_lo = (H - BAND[1] * R) if up else (H + BAND[0] * R)
        leg_start = d["st"][r.a_i]
        leg_end = d["ct"][r.p_i]
        arm_ns = d["ct"][r.arm_i]
        sl15 = slice(r.a_i + 2, r.p_i + 1)
        pol15 = (b15 if up else s15)[sl15]
        z15 = _pick(pol15, g15lo[sl15], g15hi[sl15], band_lo, band_hi, up)
        if z15 is None:
            continue
        levels = [(z15[1] if up else z15[0], False)]
        i5a, i5b = np.searchsorted(s5, leg_start), np.searchsorted(t5, leg_end, "right")
        if i5b > i5a:
            z5 = _pick((u5 if up else dn5)[i5a:i5b], g5lo[i5a:i5b], g5hi[i5a:i5b], z15[0], z15[1], up)
            if z5 is not None:
                i1a, i1b = np.searchsorted(s1, leg_start), np.searchsorted(t1, leg_end, "right")
                if i1b > i1a:
                    z1 = _pick((u1 if up else dn1)[i1a:i1b], g1lo[i1a:i1b], g1hi[i1a:i1b], z5[0], z5[1], up)
                    if z1 is not None:
                        levels.append((z1[1] if up else z1[0], True))
        pre_lo = d["l"][r.p_i + 1:r.arm_i + 1].min()
        pre_hi = d["h"][r.p_i + 1:r.arm_i + 1].max()
        for lvl, nested in levels:
            if (pre_lo <= lvl) if up else (pre_hi >= lvl):
                continue
            j = first_touch(m, arm_ns, arm_ns + WAIT_BARS * bar_ns, lvl, up, cancel=H)
            if j < 0:
                continue
            if (m.l[j] <= L) if up else (m.h[j] >= L):
                continue
            rows.append((m.t[j] + ONE_MIN, int(r.dir), L, H, nested))
    if not rows:
        return pd.DataFrame(columns=COLS)
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "target_px", "nested"])
    out = out.sort_values(["t", "nested"]).reset_index(drop=True)
    dec = to_ts(out["t"])
    return pd.DataFrame({"decision_time": dec, "available_at": dec,
                         "direction": out["direction"].to_numpy(),
                         "stop_px": out["stop_px"].to_numpy(), "target_px": out["target_px"].to_numpy(),
                         "nested": out["nested"].to_numpy(bool)})


OP = {"rules": [
    "15m displacement legs exactly as optimal-trade-entry reading a (2/2 swings, close-through break, anchor -> first "
    "swing extreme after the break, armed at that swing's confirmation)",
    "setup requires a same-direction 15m FVG formed inside the leg overlapping the 0.62-0.79 OTE band (first-reached one)",
    "15m arm: limit at that gap's near edge (clipped to the band)",
    "nested arm: a same-direction 5m FVG formed inside the leg overlapping the 15m zone, then a same-direction 1m FVG "
    "formed inside the leg overlapping that overlap; limit at the near edge of the innermost intersection",
    "fills: first M1 touch within 20 x 15m bars of arming, before a new leg extreme, not pre-tapped before arming; "
    "decide at the touch M1 close, enter next open; stop = leg anchor, target = leg extreme, 5h hold",
    "gate_test on the union book, mask = nested; 1m stands in for the 15s chart (not in the data)"],
    "params": {"tf": TF, "ladder": "15m/5m/1m", "band": list(BAND), "wait_bars": WAIT_BARS,
               "max_hold": MAX_HOLD, "swing": "2/2"}}
SRC = {"tf": "corpus: ivirRu3fc4o 'a 15 second fair value gap right here nested in between the 15 minute' (15m top of stack)",
       "ladder": "declared-before-run: corpus ladder 15m/5m/15s is 'the example'; M1 is the finest data, so 15m/5m/1m",
       "band": "corpus: 0bH_kkG2q6s 'defined as retracement between 62 and 79 from the low to the high'",
       "wait_bars": "declared-before-run: same as optimal-trade-entry (20 structure bars)",
       "max_hold": "declared-before-run: 20 structure (15m) bars",
       "swing": "phase3: locked fractal 2/2"}

if __name__ == "__main__":
    ev = cl.cache_frame("nested_fvg_15_5_1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["nested"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "nested", mask_available_at="decision_time", max_hold=MAX_HOLD)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
                                   "ties", "ctrl_overlap", "sanity")})
    cl.write_result("nested-fvg-entry-refinement", None, res, operationalization=OP, params_source=SRC,
                    script=__file__, probe=probe,
                    notes="Stated benefit is drawdown (MAE), which the harness scores only via R; the test asks whether "
                          "the nested entry's control-adjusted R beats the unrefined 15m-gap entry at the same setups.")
