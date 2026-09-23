"""optimal-trade-entry (contested) — batch entry_own_02b.

Reading a: trade_test of the bare OTE entry. After a 15m structure break (close
beyond the last confirmed 2/2 swing), fib the displacement leg (anchor low that
broke structure -> first swing high after the break, wicks). Once that swing is
confirmed, rest a limit at 0.705 (his preferred OTE entry); stop at the leg anchor
(1.0), target the leg extreme (0.0). Missed if price makes a new extreme first or
does not come back within 20 bars.

Reading b: gate_test on the same book — does a same-direction 15m FVG inside the
leg overlapping the 0.62-0.79 band (the "PD array in the OTE" confluence) improve it?
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
                     fvg_arrays, to_ts, ONE_MIN)

TF = "15min"
ENTRY_FIB = 0.705
BAND = (0.62, 0.79)
WAIT_BARS = 20
MAX_HOLD = "5h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px",
        "fvg_in_ote"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 500:
        return pd.DataFrame(columns=COLS)
    b, d = bars_with_swings(m1, TF, 2, 2)
    legs = displacement_legs(d, right=2)
    m = M1(m1)
    bull_g, bear_g, glo, ghi = fvg_arrays(d)
    bar_ns = np.int64(15) * ONE_MIN
    rows = []
    for r in legs.itertuples(index=False):
        bull = r.dir == 1
        L, H = float(r.L), float(r.H)
        R = (H - L) if bull else (L - H)
        if not R > 0:
            continue
        lvl = (H - ENTRY_FIB * R) if bull else (H + ENTRY_FIB * R)
        # already tapped before the swing was confirmed -> no resting order possible
        pre = d["l"][r.p_i + 1:r.arm_i + 1].min() if bull else d["h"][r.p_i + 1:r.arm_i + 1].max()
        if (pre <= lvl) if bull else (pre >= lvl):
            continue
        arm_ns = d["ct"][r.arm_i]
        j = first_touch(m, arm_ns, arm_ns + WAIT_BARS * bar_ns, lvl, bull, cancel=H)
        if j < 0:
            continue
        # touch bar itself breaching the stop -> stopped before the order could be acted on
        if (m.l[j] <= L) if bull else (m.h[j] >= L):
            continue
        dec = m.t[j] + ONE_MIN
        # FVG confluence: same-direction gap formed inside the leg (a_i..p_i), overlapping the band
        b_hi = (H - BAND[0] * R) if bull else (H + BAND[1] * R)
        b_lo = (H - BAND[1] * R) if bull else (H + BAND[0] * R)
        seg = slice(r.a_i + 2, r.p_i + 1)
        g = bull_g[seg] if bull else bear_g[seg]
        ov = g & (ghi[seg] >= b_lo) & (glo[seg] <= b_hi)
        rows.append((dec, dec, int(r.dir), L, H, bool(ov.any())))
    if not rows:
        return pd.DataFrame(columns=COLS)
    out = pd.DataFrame(rows, columns=COLS)
    out["decision_time"] = to_ts(out["decision_time"])
    out["available_at"] = to_ts(out["available_at"])
    return out.sort_values("decision_time").reset_index(drop=True)


OP = {"rules": [
    "15m bars (forex grid irrelevant below 4h); fractal swings 2/2 confirmed at the 2nd right bar's close",
    "displacement = a 15m CLOSE beyond the last confirmed swing high (bull) / low (bear)",
    "leg anchor = extreme low (bull) from that swing to the break bar; leg end = first swing high at/after the break; "
    "leg void if the anchor is exceeded before the leg-end swing is confirmed",
    "armed at the leg-end swing's confirmation; skip if 0.705 was already tapped before arming",
    "entry: first M1 bar within 20 x 15m bars that trades to the 0.705 retracement before any new leg extreme "
    "(a bar doing both = cancelled); decide at that M1 close, enter next M1 open",
    "stop = leg anchor (1.0), target = leg extreme (0.0), max hold 5h",
    "reading b gate: a same-direction 15m FVG formed inside the leg whose zone overlaps the 0.62-0.79 band"],
    "params": {"tf": TF, "swing": "2/2", "entry_fib": ENTRY_FIB, "band": list(BAND),
               "wait_bars": WAIT_BARS, "max_hold": MAX_HOLD, "ctrl_tod_tol_min": 30}}
SRC = {"tf": "corpus: gZLLuB_rmis / YAML timeframes htf [1H, 15m]",
       "swing": "phase3: locked fractal 2/2 (conjunction_preregistration)",
       "entry_fib": "corpus: 1YRs4Z1lMws 'That's this zone from the 62 to the 79 including the midpoint of 705.' (0.705 preferred entry)",
       "band": "corpus: 0bH_kkG2q6s 'defined as retracement between 62 and 79 from the low to the high'",
       "wait_bars": "declared-before-run: an OTE limit left unfilled for 20 structure bars is treated as missed",
       "max_hold": "declared-before-run: 20 structure (15m) bars",
       "ctrl_tod_tol_min": "declared-before-run: README trap 9 — setup not about timing but clusters in active hours"}

if __name__ == "__main__":
    ev = cl.cache_frame("ote_15m_0705_w20", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict(), ev["fvg_in_ote"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD, ctrl_tod_tol_min=30)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
                                   "exposure_bars", "ties", "ctrl_overlap")})
    cl.write_result("optimal-trade-entry", "a", res, operationalization=OP, params_source=SRC,
                    script=__file__, probe=probe,
                    notes="Reading a: bare 0.705 OTE limit on 15m displacement legs, stop at anchor, target leg extreme. "
                          "HTF-bias precondition not applied (no mechanical bias definition in this unit).")
    resb = cl.gate_test(ev, "fvg_in_ote", mask_available_at="decision_time", max_hold=MAX_HOLD,
                        ctrl_tod_tol_min=30)
    print({k: resb.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
                                    "gate_rate")})
    cl.write_result("optimal-trade-entry", "b", resb, operationalization=OP, params_source=SRC,
                    script=__file__, probe=probe,
                    notes="Reading b: gate = OTE band overlaps a same-direction 15m FVG in the leg (PD-array confluence); "
                          "baseline = the reading-a OTE book. Gate known at arming (all inputs precede the decision).")
