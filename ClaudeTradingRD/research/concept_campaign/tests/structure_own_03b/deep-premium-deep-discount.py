"""deep-premium-deep-discount (TTrades, b6yvRKf8haE) — gate_test.

Claim: on a buy day, buys are sought in DEEP discount (price below BOTH the midnight open
and the 08:30 open); sells in DEEP premium (above both). '+' = entries in the deep zone
beat entries elsewhere.

Operationalisation (declared before the first run):
  * baseline book = phase-3 rung-0 15m CISD (series_open, swing 2/2, max_wait 3, stop =
    protected swing, 2R), restricted to decisions made after BOTH opens exist on the same
    trading day and before the 17:00 NY halt: NY clock 08:31-17:00. The CISD direction
    stands in for "buy day / sell day" (the direction the setup is being traded).
  * price = the CISD confirming bar's close (the decision price).
  * gate deep = long and px < min(midnight open, 08:30 open), or short and px > max(...).
    Complement = every other baseline trade (plain zone, or the wrong side).
  * max_hold 150min (10 x 15m bars, phase 3).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402

MAX_HOLD = "150min"


def detect(m1):
    ev, _ = C.cisd_book(m1, "15min")
    t = pd.DatetimeIndex(ev["decision_time"])
    ev = ev[cl.in_window(t, "08:31", "17:00")].reset_index(drop=True)
    t = pd.DatetimeIndex(ev["decision_time"])
    mo = cl.open_at(t, "00:00", m1=m1)
    eo = cl.open_at(t, "08:30", m1=m1)
    ok = mo["price"].notna().to_numpy() & eo["price"].notna().to_numpy()
    ev = ev[ok].reset_index(drop=True)
    mo_p, eo_p = mo["price"].to_numpy()[ok], eo["price"].to_numpy()[ok]
    lo, hi = np.minimum(mo_p, eo_p), np.maximum(mo_p, eo_p)
    px, d = ev["px"].to_numpy(), ev["direction"].to_numpy()
    ev["midnight_open"], ev["open_0830"] = mo_p, eo_p
    ev["deep"] = ((d == 1) & (px < lo)) | ((d == -1) & (px > hi))
    return ev.drop(columns=["bar_pos"])


if __name__ == "__main__":
    ev = cl.cache_frame("dpdd_cisd15_0831_1700", lambda: detect(cl.load_m1()))
    print(len(ev), ev.deep.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "deep", mask_available_at="decision_time", max_hold=MAX_HOLD)
    C.show(res)
    p = cl.write_result(
        "deep-premium-deep-discount", None, res,
        operationalization={"rules": [
            "baseline: 15m rung-0 CISD (series_open, 2/2 swing, max_wait 3), stop protected swing, 2R, 150min time exit",
            "only decisions at NY 08:31-17:00 on a trading day that has both the 00:00 and 08:30 NY opens",
            "CISD direction = the day's side (buy day / sell day)",
            "gate deep: long with confirming close below BOTH opens, or short with close above BOTH; complement = all other baseline trades"],
            "params": {"baseline_tf": "15min", "max_wait": 3, "rr": 2.0, "max_hold": MAX_HOLD,
                       "window": "08:31-17:00 NY", "opens": ["00:00", "08:30"],
                       "price": "confirming bar close"}},
        params_source={
            "baseline_tf": "phase3: primary stack entry TF (15m), concept ltf 15m/5m/1m",
            "max_wait": "phase3: locked CISD config max_wait=3",
            "rr": "phase3: locked 2R target",
            "max_hold": "phase3: 10 entry-TF bars",
            "window": "declared-before-run: from the first minute both opens exist to the 17:00 NY halt",
            "opens": "corpus: b6yvRKf8haE 'if you're below both of those it is a deep discount'",
            "price": "declared-before-run: the decision bar's close is where the entry is being judged"},
        script=__file__, probe=probe,
        notes="Direction of the CISD stands in for the day's side; the concept gives no separate buy-day rule.")
    print(p)
