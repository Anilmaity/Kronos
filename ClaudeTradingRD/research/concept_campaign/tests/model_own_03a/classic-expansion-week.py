"""classic-expansion-week — Classic Expansion (weekly profile), TTrades own voice.

Reading (the concept is `specified`, one reading):
  * candidate day = Monday or Tuesday session (18:00 NY roll);
  * it closes as a daily C2 closure (method spec §3.2) — bullish: takes the previous
    day's low and closes back above it; bearish mirrored;
  * its low (bullish) is the low of the week so far (Tuesday: below Monday's low);
  * an hourly CISD in the same direction exists inside that daily candle (§2.4 step 3);
  * a two-sided C2 is kept only on the side carrying the hourly CISD; both -> skip;
  * trade: enter at the next session's open (C3), stop at the confirmed extreme,
    target 2R (method spec §5.3 floor), hold to the week's close (Friday 17:00 NY)
    — "Friday caps off the weekly range" — so C3 and C4 are both held.
Test: trade_test vs the matched random-entry control, claim '+'.
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

CID = "classic-expansion-week"
RR = 2.0
DAYS = (0, 1)                     # Monday, Tuesday


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily_frame(m1)
    h1 = cl.build_bars(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold", "week"]
    if len(d) < 3:
        return pd.DataFrame(columns=cols)
    bull, bear = c2_flags(d)
    rows = []
    for i in range(1, len(d)):
        r = d.iloc[i]
        if r["wd"] not in DAYS:
            continue
        same_week_prev = r["p_week"] == r["week"]
        sides = []
        if bull[i] and (r["wd"] == 0 or (same_week_prev and r["low"] < r["p_low"])):
            if h1_cisd(h1, d.index[i], r["close_time"], "bullish") is not None:
                sides.append(1)
        if bear[i] and (r["wd"] == 0 or (same_week_prev and r["high"] > r["p_high"])):
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
    "candidate = Monday or Tuesday session that is a daily C2 closure (bullish: low<prev low, "
    "close>prev low; bearish mirrored) and is the week's extreme so far",
    "an hourly CISD (close through the first open of the opposing series into the day's "
    "extreme, anywhere inside the daily candle) in the same direction; two-sided -> the side "
    "with the CISD, both -> skip",
    "enter at the first M1 open after the candidate day closes (C3 open); stop at the "
    "candidate's extreme; target 2R; hold to Friday 17:00 NY (trading-minute hold, "
    "hold_basis='bars')"],
    "params": {"days": "Mon,Tue", "rr": RR, "cisd_scope": "range",
               "cisd_level_rule": "series_open", "day_open_hour": 18,
               "min_coverage": 0.5, "exit": "Friday 17:00 NY",
               "hold_basis": "bars", "ctrl_tod_tol_min": 30}}
SRC = {"days": "corpus: Qt7Ek4keMzs 'We want to see the weekly candle open low then reach for "
               "its high' — method_spec §2.5 weekly profiles: Classic Expansion extreme forms "
               "Monday or Tuesday",
       "rr": "method_spec: §5.3 '2R is the floor'",
       "cisd_scope": "method_spec: §2.4 [P] scope default 'range' (detectors.bias default)",
       "cisd_level_rule": "method_spec: §4.2 'carry first-candle-open as the sensible default'",
       "day_open_hour": "session_window_fit: settled 18:00 NY daily roll / method_spec §1.4",
       "min_coverage": "declared-before-run: drop stub sessions (README trap 6)",
       "exit": "corpus: Qt7Ek4keMzs — classic-expansion definition 'Friday then caps off the "
               "weekly range'; trade C3 and C4",
       "hold_basis": "declared-before-run: week-end exit measured in trading minutes so the "
                     "control's exposure matches (README trap 7)",
       "ctrl_tod_tol_min": "declared-before-run: every entry sits at the 18:00 reopen; hold "
                           "the NY clock fixed (README trap 9)"}

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
                        notes="Weekly trades clustered by week id. Hold is the trading-minute "
                              "span to Friday 17:00 NY with hold_basis='bars'.")
    print(p)
