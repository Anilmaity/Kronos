"""intraweek-reversal-week — Intraweek Reversal (weekly profile), TTrades own voice. CONTESTED.

Both readings trade a daily swing point that is NOT the weekly extreme, in the direction
the early week already expanded, then hold the continuation days to Friday's close.

Reading a (Shorts T3aqrI6P4G8 — "leave Tuesday alone", wait for the Wednesday swing):
  * Monday AND Tuesday are both continuation closures in direction d (method spec §2.3:
    bullish close > previous day's high; bearish mirrored);
  * Wednesday is a daily C2 closure in direction d (bullish: low < Tuesday low,
    close > Tuesday low) whose extreme is NOT the week's (bullish: Wednesday low > Monday low);
  * hourly CISD in direction d inside Wednesday; enter Thursday open.
Reading b (series FvOUvQ7odiw — Monday expands away from the weekly open, the reversal
day floats):
  * Monday is a continuation closure in direction d (the week's direction);
  * the FIRST day X in Tue/Wed/Thu that is a daily C2 closure in direction d whose extreme
    is not the week's so far, with an hourly CISD in direction d inside X; enter the next
    session's open.
Both: stop at the reversal day's extreme (the protected swing), target 2R (§5.3),
hold to Friday 17:00 NY in trading minutes. trade_test, claim '+'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                            # noqa: E402
from _common import (daily_frame, c2_flags, cont_flags, h1_cisd,     # noqa: E402
                     friday_close_utc, trading_minutes)

CID = "intraweek-reversal-week"
RR = 2.0
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold", "week"]


def _row(r, s):
    dec = pd.Timestamp(r["close_time"])
    hold = trading_minutes(dec, friday_close_utc(r["week"]))
    if hold <= pd.Timedelta(0):
        return None
    return {"decision_time": dec, "available_at": dec, "direction": s,
            "stop_px": float(r["low"] if s > 0 else r["high"]), "rr": RR,
            "max_hold": hold, "week": str(pd.Timestamp(r["week"]).date())}


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily_frame(m1)
    h1 = cl.build_bars(m1, "1h")
    if len(d) < 4:
        return pd.DataFrame(columns=COLS)
    bull, bear = c2_flags(d)
    up, dn = cont_flags(d)
    rows = []
    for i in range(2, len(d)):
        r, t, m = d.iloc[i], d.iloc[i - 1], d.iloc[i - 2]
        if not (r["wd"] == 2 and t["wd"] == 1 and m["wd"] == 0
                and r["week"] == t["week"] == m["week"]):
            continue
        sides = []
        if up[i - 1] and up[i - 2] and bull[i] and r["low"] > m["low"]:
            if h1_cisd(h1, d.index[i], r["close_time"], "bullish") is not None:
                sides.append(1)
        if dn[i - 1] and dn[i - 2] and bear[i] and r["high"] < m["high"]:
            if h1_cisd(h1, d.index[i], r["close_time"], "bearish") is not None:
                sides.append(-1)
        if len(sides) != 1:
            continue
        row = _row(r, sides[0])
        if row:
            rows.append(row)
    return pd.DataFrame(rows, columns=COLS)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily_frame(m1)
    h1 = cl.build_bars(m1, "1h")
    if len(d) < 4:
        return pd.DataFrame(columns=COLS)
    bull, bear = c2_flags(d)
    up, dn = cont_flags(d)
    rows = []
    wk = d["week"].to_numpy()
    wd = d["wd"].to_numpy()
    i = 0
    n = len(d)
    while i < n:
        if wd[i] != 0 or not (up[i] or dn[i]):
            i += 1
            continue
        s = 1 if up[i] else -1
        lo, hi = d["low"].iloc[i], d["high"].iloc[i]
        j = i + 1
        while j < n and wk[j] == wk[i] and wd[j] <= 3:
            r = d.iloc[j]
            ok = False
            if s > 0 and bull[j] and r["low"] > lo:
                ok = h1_cisd(h1, d.index[j], r["close_time"], "bullish") is not None
            if s < 0 and bear[j] and r["high"] < hi:
                ok = h1_cisd(h1, d.index[j], r["close_time"], "bearish") is not None
            if ok:
                row = _row(r, s)
                if row:
                    rows.append(row)
                break
            lo, hi = min(lo, r["low"]), max(hi, r["high"])
            j += 1
        i = j if j > i else i + 1
    return pd.DataFrame(rows, columns=COLS)


BASE_SRC = {
    "rr": "method_spec: §5.3 '2R is the floor'",
    "cisd_scope": "method_spec: §2.4 [P] scope default 'range'",
    "cisd_level_rule": "method_spec: §4.2 first-candle-open default",
    "day_open_hour": "session_window_fit: settled 18:00 NY daily roll / method_spec §1.4",
    "min_coverage": "declared-before-run: drop stub sessions (README trap 6)",
    "expansion": "method_spec: §2.3 continuation closure = takes the previous candle's "
                 "extreme and closes outside (the corpus gives no threshold for 'expands')",
    "exit": "corpus: T3aqrI6P4G8 'we could be looking for Thursday to get a continuation' — "
            "Thursday and Friday continuations, so hold to Friday 17:00 NY",
    "hold_basis": "declared-before-run: week-end exit in trading minutes (README trap 7)",
    "ctrl_tod_tol_min": "declared-before-run: entries all at the 18:00 reopen (README trap 9)"}
BASE_PARAMS = {"rr": RR, "cisd_scope": "range", "cisd_level_rule": "series_open",
               "day_open_hour": 18, "min_coverage": 0.5,
               "expansion": "continuation closure (close beyond prev day extreme)",
               "exit": "Friday 17:00 NY", "hold_basis": "bars", "ctrl_tod_tol_min": 30}

READINGS = {
    "a": (detect_a, {"rules": [
        "Monday and Tuesday both continuation closures in direction d",
        "Wednesday = daily C2 closure in direction d whose extreme is not the week's "
        "(bullish: Wed low > Mon low)",
        "hourly CISD in direction d inside Wednesday",
        "enter Thursday open; stop Wednesday extreme; 2R; hold to Friday 17:00 NY"],
        "params": {**BASE_PARAMS, "reversal_day": "Wednesday"}},
        {**BASE_SRC, "reversal_day": "corpus: T3aqrI6P4G8 'We leave Tuesday alone as it's "
                                     "already expanded a fair bit' / 'Wait for a new swing "
                                     "point to form'"}),
    "b": (detect_b, {"rules": [
        "Monday is a continuation closure in direction d (expands away from the weekly open)",
        "first day in Tue/Wed/Thu that is a daily C2 closure in direction d, extreme not the "
        "week's so far, with an hourly CISD in direction d inside it",
        "enter at the next session open; stop at that day's extreme; 2R; hold to Friday "
        "17:00 NY"],
        "params": {**BASE_PARAMS, "reversal_day": "first qualifying of Tue/Wed/Thu"}},
        {**BASE_SRC, "reversal_day": "corpus: FvOUvQ7odiw 'where we don't have the reversal "
                                     "forming the high of the week' — reversal day floats "
                                     "(Wednesday, or Thursday if Wednesday consolidates)"}),
}

if __name__ == "__main__":
    for rd, (fn, op, src) in READINGS.items():
        ev = cl.cache_frame(f"{CID}_{rd}_v1", lambda: fn(cl.load_m1()))
        print(rd, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(fn, ev, lookback="30D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, hold_basis="bars", ctrl_tod_tol_min=30, cluster="week")
        for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "exposure_bars", "ctrl_overlap"):
            print(" ", k, res.get(k))
        p = cl.write_result(CID, rd, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe,
                            notes="Weekly trades clustered by week id; hold to Friday 17:00 NY "
                                  "in trading minutes (hold_basis='bars').")
        print(p)
