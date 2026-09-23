"""eq-if-then-pd-array-match — trade_test.

Previous completed day's EQ = 0.5 of its wick range. Long branch: a 1H CISD whose
protected swing low sits in the DISCOUNT half [PDL, EQ] (the half consistent with a
bullish read) -> long, stop at that protected swing (the day's invalidation),
target PDH (the far side). Short branch mirrored: protected high in [EQ, PDH],
target PDL. Skip when the target was already taken today or sits at/behind the
entry ("range already expanded -> do not force it").
Claim (+): beats a matched random entry. All parameters declared before the first run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, cisd_book, day_context, run_and_print, PHASE3_SRC  # noqa: E402

TF = "1h"
MAX_HOLD = "10h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    ev = cisd_book(m1, TF)
    if ev.empty:
        return ev.assign(target_px=pd.Series(dtype=float))
    ctx = day_context(m1, ev["decision_time"])
    pdh, pdl = ctx["pdh"].to_numpy(), ctx["pdl"].to_numpy()
    eq = 0.5 * (pdh + pdl)
    d = ev["direction"].to_numpy()
    sw = ev["stop_px"].to_numpy()
    px = ev["confirm_close"].to_numpy()
    long = d == 1
    in_half = np.where(long, (sw >= pdl) & (sw <= eq), (sw >= eq) & (sw <= pdh))
    tgt = np.where(long, pdh, pdl)
    untaken = np.where(long, ctx["run_hi"].to_numpy() < pdh, ctx["run_lo"].to_numpy() > pdl)
    ahead = d * (tgt - px) > 0
    ok = np.isfinite(eq) & in_half & untaken & ahead
    out = ev.assign(target_px=tgt, pd_eq=eq)[ok].reset_index(drop=True)
    return out.drop(columns=["rr"])


if __name__ == "__main__":
    ev = cl.cache_frame(f"eqifthen_{TF}_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    run_and_print(res)
    op = {"rules": [
        "previous completed trading day (18:00 NY roll, >= 600 M1 bars): EQ = (PDH + PDL) / 2, wick to wick",
        "entry trigger: phase-3 bare 1H CISD (series_open, 2/2 swings, max_wait 3, min_series 1) = the "
        "confirming CISD at a PD array (the protected swing is itself one of the listed PD arrays)",
        "long only if the CISD's protected swing low lies in [PDL, EQ]; short only if the protected high lies in [EQ, PDH]",
        "stop = that protected swing (the day's invalidation); target = PDH (long) / PDL (short)",
        "skip if today's running high >= PDH (long) / low <= PDL (short) already, or target not beyond the confirm close",
        "decide at the CISD bar close, enter next M1 open, time exit after 10h"],
        "params": {"tf": TF, "max_hold": MAX_HOLD, "eq": "0.5 of previous day wick range",
                   "target": "PDH/PDL", "day_open_hour": 18, "min_day_m1": 600}}
    src = {"tf": "corpus: IPZjNI1B5a0 ltf 1H ('confirm with a change in the state of delivery'); phase3 CISD config",
           "max_hold": PHASE3_SRC + " — 10 entry-TF bars",
           "eq": "corpus: IPZjNI1B5a0 'Mark the previous higher-timeframe candle's EQ (0.5, wick high to wick low)'",
           "target": "corpus: IPZjNI1B5a0 'if the EQ is respected then we can trade lower through previous day low'",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "min_day_m1": "declared-before-run: skip stub days (trap 6)"}
    notes = ("The 'close through the EQ against the branch' invalidation and the 'three candles of expansion' "
             "pause are not applied (the stop is the stated protected swing; the pause is stated once by example). "
             "PD-array precedence is not stated; the CISD's own protected swing is used as the PD array.")
    p = cl.write_result("eq-if-then-pd-array-match", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print("wrote", p)
