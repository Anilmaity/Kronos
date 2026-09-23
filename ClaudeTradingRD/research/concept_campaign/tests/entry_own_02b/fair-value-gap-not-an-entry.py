"""fair-value-gap-not-an-entry — batch entry_own_02b.

Claim (u8bnmaih_hA / r7yW6ou1LDs, method spec §4.6): a resting limit inside a fair
value gap is not an entry — wait for a reaction inside the gap that validates a new
order block (a close through the opposing candles = CISD), enter on that close with
the stop on that structure. Validated entries should beat gap-limit entries.

Test: gate_test on the union book of both entry types at the SAME 1h gaps
(1h structure / 5m execution = the playbook pair):
  arm "limit":     first return into a 1h FVG -> long at the near edge, stop beyond
                   the gap's far edge, 2R.
  arm "validated": after that return, the first 5m CISD (series_open, 2/2, max_wait 3)
                   whose swing extreme formed after the touch at/inside the gap, within
                   12 x 5m bars of the touch, with no 5m close beyond the gap's far
                   edge first -> enter on the CISD close, stop at the protected swing, 2R.
mask = validated. claim '+': control-adjusted R of validated > limit.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                    # noqa: E402
from detectors.cisd import cisd_events                      # noqa: E402
from _common import M1, first_touch, fvg_arrays, to_ts, ns, ONE_MIN   # noqa: E402

HTF = "1h"
LTF = "5min"
RETURN_WAIT_H = 24
VALID_WAIT = 12
RR = 2.0
MAX_HOLD = "10h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "validated"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 2000:
        return pd.DataFrame(columns=COLS)
    hb = cl.build_bars(m1, HTF)
    d = {"h": hb["high"].to_numpy(float), "l": hb["low"].to_numpy(float)}
    bull, bear, glo, ghi = fvg_arrays(d)
    hct = ns(hb["close_time"])
    lb = cl.build_bars(m1, LTF)
    lst, lct, lc = ns(lb.index), ns(lb["close_time"]), lb["close"].to_numpy(float)
    ce = cisd_events(lb[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if len(ce):
        c_dir = np.where(ce["direction"] == "bullish", 1, -1)
        c_ext = ns(ce["extreme_time"])
        c_conf_i = np.searchsorted(lst, ns(ce["confirm_time"]))
        c_ps = ce["protected_swing"].to_numpy(float)
    else:
        c_dir = c_ext = c_conf_i = c_ps = np.zeros(0)
    m = M1(m1)
    last_ok = m.t[-1] + ONE_MIN
    rows = []
    hour = np.int64(60) * ONE_MIN
    for i in np.flatnonzero(bull | bear):
        if hct[i] > last_ok:
            continue
        up = bool(bull[i])
        near, far = (ghi[i], glo[i]) if up else (glo[i], ghi[i])
        j = first_touch(m, hct[i], hct[i] + RETURN_WAIT_H * hour, near, up, cancel=None)
        if j < 0:
            continue
        # arm "limit" (drops a return bar that also trades through the far edge: the
        # fill-then-stop inside one M1 cannot be entered next-open — conservative for the claim)
        through = (m.l[j] <= far) if up else (m.h[j] >= far)
        if not through:
            rows.append((m.t[j] + ONE_MIN, 1 if up else -1, far, False))
        # arm "validated"
        ti = int(np.searchsorted(lst, m.t[j], "right") - 1)     # 5m bar containing the touch
        if ti < 0:
            continue
        cand = np.flatnonzero((c_dir == (1 if up else -1)) & (c_ext >= lst[ti]) &
                              (c_conf_i >= ti) & (c_conf_i <= ti + VALID_WAIT))
        for k in cand[np.argsort(c_conf_i[cand], kind="stable")]:
            ps = c_ps[k]
            if (ps > near) if up else (ps < near):
                continue                       # reaction extreme not inside/at the gap
            ci = int(c_conf_i[k])
            seg = lc[ti:ci + 1]
            if ((seg < far).any()) if up else ((seg > far).any()):
                break                          # closed through the gap first: invalidated
            if lct[ci] > last_ok:
                break
            rows.append((lct[ci], 1 if up else -1, ps, True))
            break
    if not rows:
        return pd.DataFrame(columns=COLS)
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "validated"])
    out = out.sort_values(["t", "validated"]).reset_index(drop=True)
    dec = to_ts(out["t"])
    return pd.DataFrame({"decision_time": dec, "available_at": dec,
                         "direction": out["direction"].to_numpy(),
                         "stop_px": out["stop_px"].to_numpy(), "rr": RR,
                         "validated": out["validated"].to_numpy(bool)})


OP = {"rules": [
    "1h FVGs (3-bar, wicks), known at the 3rd bar's close; direction = the gap's polarity (retracement into it)",
    "first return = first M1 bar within 24h trading to the gap's near edge",
    "limit arm: decide at that M1 close, enter next open, stop = gap far edge, 2R (return bars that also trade "
    "through the far edge are dropped: cannot be entered next-open; this favours the limit arm)",
    "validated arm: first 5m CISD (series_open, 2/2, max_wait 3) in the gap's direction whose swing extreme bar starts "
    "at/after the touch's 5m bar, whose extreme is at/inside the gap (not beyond the near edge), confirmed within 12 "
    "5m bars of the touch, with no 5m close beyond the far edge first; enter on the CISD close, stop = protected swing, 2R",
    "gate_test on the union book, mask = validated, max hold 10h"],
    "params": {"htf": HTF, "ltf": LTF, "return_wait_h": RETURN_WAIT_H, "valid_wait_5m": VALID_WAIT,
               "cisd": "series_open 2/2 max_wait 3", "rr": RR, "max_hold": MAX_HOLD}}
SRC = {"htf": "method_spec: §1.2 pairing 1-hour -> 5-minute (playbook); YAML ltf [1H, 15m, 5m]",
       "ltf": "method_spec: §1.2 pairing 1-hour -> 5-minute",
       "return_wait_h": "declared-before-run: a gap not revisited within 24h is dropped",
       "valid_wait_5m": "declared-before-run: the validating reaction must come within one 1h candle (12 x 5m) of the touch",
       "cisd": "phase3: rung-0 CISD config (series_open, 2/2, max_wait=3); method_spec §4.2 'validates those candles as an order block'",
       "rr": "corpus: YAML execution targets [2R]",
       "max_hold": "phase3: 10 structure-TF (1h) bars"}

if __name__ == "__main__":
    ev = cl.cache_frame("fvg_not_entry_1h_5m", lambda: detect(cl.load_m1()))
    print(len(ev), ev["validated"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "validated", mask_available_at="decision_time", max_hold=MAX_HOLD)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
                                   "ties", "ctrl_overlap", "sanity")})
    cl.write_result("fair-value-gap-not-an-entry", None, res, operationalization=OP, params_source=SRC,
                    script=__file__, probe=probe,
                    notes="Union book of gap-limit and CISD-validated entries at the same 1h gaps; mask = validated. "
                          "Control adjustment removes the stop-size difference between arms.")
