"""midweek-reversal-week — Midweek Reversal (weekly profile), TTrades own voice.

Reading (`specified`, one reading):
  * Monday and Tuesday both close against the setup (bullish: both down-close days,
    close < open), building the weekly wick; both sessions must be present;
  * Wednesday closes as a daily C2 closure in the setup direction (method spec §3.2:
    bullish low < Tuesday low and close > Tuesday low) and its low is the week's low
    (below Monday's low too);
  * an hourly CISD in the setup direction inside Wednesday (§2.4 step 3); two-sided
    Wednesday -> the side with the CISD, both -> skip;
  * trade Thursday (C3) and Friday (C4): enter at the Thursday session open, stop at
    Wednesday's extreme, target 2R (§5.3 floor), hold to Friday 17:00 NY.
The Thursday-confirmation fallback (unclean Wednesday) is not traded: it is a second
entry path the concept itself calls a fallback.
Test: trade_test vs matched random entry, claim '+'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                            # noqa: E402
from _common import (daily_frame, c2_flags, h1_cisd, friday_close_utc,  # noqa: E402
                     trading_minutes)

CID = "midweek-reversal-week"
RR = 2.0


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily_frame(m1)
    h1 = cl.build_bars(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold", "week"]
    if len(d) < 4:
        return pd.DataFrame(columns=cols)
    bull, bear = c2_flags(d)
    rows = []
    for i in range(2, len(d)):
        r, t, m = d.iloc[i], d.iloc[i - 1], d.iloc[i - 2]
        if not (r["wd"] == 2 and t["wd"] == 1 and m["wd"] == 0
                and r["week"] == t["week"] == m["week"]):
            continue
        sides = []
        if (bull[i] and t["close"] < t["open"] and m["close"] < m["open"]
                and r["low"] < m["low"]):
            if h1_cisd(h1, d.index[i], r["close_time"], "bullish") is not None:
                sides.append(1)
        if (bear[i] and t["close"] > t["open"] and m["close"] > m["open"]
                and r["high"] > m["high"]):
            if h1_cisd(h1, d.index[i], r["close_time"], "bearish") is not None:
                sides.append(-1)
        if len(sides) != 1:
            continue
        s = sides[0]
        dec = pd.Timestamp(r["close_time"])
        hold = trading_minutes(dec, friday_close_utc(r["week"]))
        if hold <= pd.Timedelta(0):
            continue
        rows.append({"decision_time": dec, "available_at": dec, "direction": s,
                     "stop_px": float(r["low"] if s > 0 else r["high"]), "rr": RR,
                     "max_hold": hold, "week": str(pd.Timestamp(r["week"]).date())})
    return pd.DataFrame(rows, columns=cols)


OP = {"rules": [
    "daily candles on the 18:00 NY roll (DST-aware); stub days (<50% of median M1 count) dropped",
    "Monday and Tuesday both close against the setup (bullish: close<open both days)",
    "Wednesday = daily C2 closure in the setup direction (bullish: low<Tue low, close>Tue low) "
    "and the week's extreme (below Monday's low)",
    "hourly CISD in the setup direction inside Wednesday (first-open series level, range scope)",
    "enter at the Thursday session open; stop at Wednesday's extreme; target 2R; hold to "
    "Friday 17:00 NY in trading minutes (hold_basis='bars')"],
    "params": {"days": "Mon+Tue against, Wed C2", "rr": RR, "cisd_scope": "range",
               "cisd_level_rule": "series_open", "day_open_hour": 18, "min_coverage": 0.5,
               "exit": "Friday 17:00 NY", "hold_basis": "bars", "ctrl_tod_tol_min": 30}}
SRC = {"days": "corpus: -gyDd_E_qD4 'Monday and Tuesday oppose our bias. Candle two closure "
               "created on Wednesday'",
       "rr": "method_spec: §5.3 '2R is the floor'",
       "cisd_scope": "method_spec: §2.4 [P] scope default 'range'",
       "cisd_level_rule": "method_spec: §4.2 first-candle-open default",
       "day_open_hour": "session_window_fit: settled 18:00 NY daily roll / method_spec §1.4",
       "min_coverage": "declared-before-run: drop stub sessions (README trap 6)",
       "exit": "method_spec: §2.5 weekly profiles — Midweek Reversal trades Thursday = C3, "
               "Friday = C4",
       "hold_basis": "declared-before-run: week-end exit in trading minutes so control "
                     "exposure matches (README trap 7)",
       "ctrl_tod_tol_min": "declared-before-run: entries all at the 18:00 reopen (README trap 9)"}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, hold_basis="bars", ctrl_tod_tol_min=30, cluster="week")
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    p = cl.write_result(CID, None, res, operationalization=OP, params_source=SRC,
                        script=__file__, probe=probe,
                        notes="Weekly trades, clustered by week id; hold to Friday 17:00 NY in "
                              "trading minutes (hold_basis='bars').")
    print(p)
