"""update_20261007 / midweek-reversal-week -- NEW claim only (draft shorts_02), vault-context run.

Source HkYIaPT8cms (Midweek Reversal Breakdown, Short, own voice): "Monday we expand higher,
Tuesday we form a reversal candle. What could we be looking for Wednesday to do here? To go
back lower into either react in a fair value gap here or here to form a swing point we can look
to trade higher", "Candle two closure, we need to go to the hourly time frame, check to see do
we have a change in the state", "So, on this next day, it is okay to be bullish", "Wednesday
reversal, Thursday continuation with a strong closure on Thursday, we can also see a Friday
continuation."

What is new vs the library reading (results/midweek-reversal-week.json, n=71, UNDERPOWERED):
the library required Monday AND Tuesday to close against the bias and Wednesday to be the
week's extreme. This example has Monday closing WITH the bias and only Tuesday against, and
never says Wednesday is the week's low. So the shape tested here is the library reading with
Monday flipped and the week-extreme requirement dropped (close-direction, exactly as the
library reading measured "against"):
  * Monday closes in the setup direction (bullish: close > open), Tuesday against it
    (bullish: close < open); Mon/Tue/Wed sessions all present in one week (stubs dropped);
  * Wednesday = daily C2 closure in the setup direction vs Tuesday (method spec §3.2,
    bullish: low < Tue low and close > Tue low); mirror for bearish;
  * hourly CISD in the setup direction inside Wednesday (§2.4 step 3, scope range, series
    open level); two-sided Wednesday -> the side with the CISD, both -> skip (§3.2);
  * trade Thursday (C3): enter at the Thursday session open (Wed 18:00 NY), stop at
    Wednesday's extreme, 2R target, exit Thursday 17:00 NY ("on this next day").
The point of interest is the one open parameter; one reading per interpretation:
  u1007a  literal: Wednesday's extreme reacts INSIDE a 4h FVG (forex grid) in the setup
          direction that formed during the Monday-Tuesday leg ("react in a fair value gap
          here or here" -- either gap counts).
  u1007b  method spec §4.1 enumeration: "a fair value gap, a high being taken out, or a low
          being taken out" -- the Wednesday C2 takes Tuesday's low, which is itself a POI,
          so no extra FVG gate.
The Friday clause (strong Thursday close -> Friday C4) is the library's existing rule, not the
new claim, and is not traded here.
Test: trade_test vs matched random entry, claim '+', clustered by week.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_03a")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                                 # noqa: E402
from _common import daily_frame, c2_flags, h1_cisd, trading_minutes, TZ  # noqa: E402
from detectors.primitives import fair_value_gaps                         # noqa: E402

CID = "midweek-reversal-week"
RR = 2.0
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold", "week"]


def thursday_close_utc(week_monday) -> pd.Timestamp:
    """Thursday 17:00 New York of the week whose Monday session date is given."""
    return (pd.Timestamp(week_monday) + pd.Timedelta(days=3, hours=17)).tz_localize(TZ).tz_convert("UTC")


def detect(m1: pd.DataFrame, need_fvg: bool) -> pd.DataFrame:
    d = daily_frame(m1)
    if len(d) < 4:
        return pd.DataFrame(columns=COLS)
    h1 = cl.build_bars(m1, "1h")
    h4 = cl.build_bars(m1, "4h")                       # forex grid (default), README trap 8
    g = fair_value_gaps(h4[["open", "high", "low", "close"]])
    g_ct = pd.DatetimeIndex(h4["close_time"])          # FVG known when its THIRD bar closes
    bull, bear = c2_flags(d)
    rows = []
    for i in range(2, len(d)):
        r, t, m = d.iloc[i], d.iloc[i - 1], d.iloc[i - 2]
        if not (r["wd"] == 2 and t["wd"] == 1 and m["wd"] == 0
                and r["week"] == t["week"] == m["week"]):
            continue
        sides = []
        for s, c2, name in ((1, bull[i], "bullish"), (-1, bear[i], "bearish")):
            if not (c2 and s * (m["close"] - m["open"]) > 0 and s * (t["close"] - t["open"]) < 0):
                continue
            if need_fvg:
                win = (g_ct > d.index[i - 2]) & (g_ct <= d.index[i])   # formed Mon-Tue, closed by Wed open
                col = "bullish_fvg" if s > 0 else "bearish_fvg"
                gw = g[win & g[col].to_numpy()]
                ext = r["low"] if s > 0 else r["high"]
                if not ((gw["gap_low"] <= ext) & (ext <= gw["gap_high"])).any():
                    continue
            if h1_cisd(h1, d.index[i], r["close_time"], name) is not None:
                sides.append(s)
        if len(sides) != 1:
            continue
        s = sides[0]
        dec = pd.Timestamp(r["close_time"])
        hold = trading_minutes(dec, thursday_close_utc(r["week"]))
        if hold <= pd.Timedelta(0):
            continue
        rows.append({"decision_time": dec, "available_at": dec, "direction": s,
                     "stop_px": float(r["low"] if s > 0 else r["high"]), "rr": RR,
                     "max_hold": hold, "week": str(pd.Timestamp(r["week"]).date())})
    return pd.DataFrame(rows, columns=COLS)


def detect_a(m1):
    return detect(m1, True)


def detect_b(m1):
    return detect(m1, False)


BASE_RULES = [
    "daily candles on the 18:00 NY roll (DST-aware); stub days (<50% of median M1 count) dropped",
    "Monday closes in the setup direction, Tuesday against it (bullish: Mon close>open, "
    "Tue close<open); mirror for bearish",
    "Wednesday = daily C2 closure in the setup direction vs Tuesday (bullish: low<Tue low, "
    "close>Tue low); Wednesday need NOT be the week's extreme",
    "hourly CISD in the setup direction inside Wednesday (first-open series level, range scope); "
    "two-sided -> CISD side, both -> skip",
    "enter at the Thursday session open (Wed 18:00 NY); stop at Wednesday's extreme; target 2R; "
    "exit Thursday 17:00 NY in trading minutes (hold_basis='bars')"]
BASE_PARAMS = {"days": "Mon with, Tue against (close direction), Wed C2", "rr": RR,
               "cisd_scope": "range", "cisd_level_rule": "series_open", "day_open_hour": 18,
               "min_coverage": 0.5, "week_extreme_required": False, "mirror": True,
               "exit": "Thursday 17:00 NY", "hold_basis": "bars", "ctrl_tod_tol_min": 30}
BASE_SRC = {
    "days": "corpus: HkYIaPT8cms 'Monday we expand higher, Tuesday we form a reversal candle.' -- "
            "measured by close direction, the exact relaxation of the library reading's 'Mon+Tue "
            "close against' (results/midweek-reversal-week.json rule 2); declared-before-run",
    "rr": "method_spec: §5.3 '2R is the floor'",
    "cisd_scope": "method_spec: §2.4 [P] scope default 'range'",
    "cisd_level_rule": "method_spec: §4.2 first-candle-open default",
    "day_open_hour": "session_window_fit: settled 18:00 NY daily roll / method_spec §1.4",
    "min_coverage": "declared-before-run: drop stub sessions (README trap 6)",
    "week_extreme_required": "corpus: draft ambiguity -- HkYIaPT8cms never says Wednesday's low "
                             "is the week's low (Monday expanded higher first); not imposed",
    "mirror": "declared-before-run: campaign convention, bearish weeks mirrored (example is bullish)",
    "exit": "corpus: HkYIaPT8cms 'So, on this next day, it is okay to be bullish' -- Thursday "
            "(C3) only; Friday is conditional on a strong Thursday close (library rule, not new)",
    "hold_basis": "declared-before-run: exit in trading minutes so control exposure matches "
                  "(README trap 7)",
    "ctrl_tod_tol_min": "declared-before-run: entries all at the 18:00 reopen (README trap 9; "
                        "vault Session Timing on Gold: reopen is a gap artefact)"}

READINGS = {
    "u1007a": (detect_a,
               BASE_RULES + ["POI (literal): Wednesday's extreme lies inside a 4h FVG in the setup "
                             "direction (forex grid) whose third bar closed between Monday's session "
                             "open and Wednesday's session open; either such gap counts"],
               {"poi": "4h FVG from the Mon-Tue leg, Wed extreme inside it", "grid4h": "forex"},
               {"poi": "corpus: HkYIaPT8cms 'go back lower into either react in a fair value gap "
                       "here or here' -- gaps left by Monday's expansion; 4h = method_spec §4.1 "
                       "'Preference is a POI on both the daily and the 4-hour'",
                "grid4h": "method_spec: §1.4 / session_window_fit forex grid default (README trap 8)"}),
    "u1007b": (detect_b,
               BASE_RULES + ["POI (method spec §4.1 enumeration): the Wednesday C2 takes Tuesday's "
                             "low ('a low being taken out'), so no extra FVG gate"],
               {"poi": "C2 sweep of Tuesday's extreme (§4.1 low/high taken out)"},
               {"poi": "method_spec: §4.1 'a fair value gap, a high being taken out, or a low "
                       "being taken out'"}),
}

if __name__ == "__main__":
    for reading, (fn, rules, xp, xs) in READINGS.items():
        ev = cl.cache_frame(f"{CID}_{reading}_thu_v1", lambda fn=fn: fn(cl.load_m1()))
        print(reading, "events", len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(fn, ev, lookback="30D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, hold_basis="bars", ctrl_tod_tol_min=30, cluster="week")
        for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                  "exposure_bars", "ties", "ctrl_overlap", "exit_mix"):
            print(" ", k, res.get(k))
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": rules, "params": {**BASE_PARAMS, **xp}},
                            params_source={**BASE_SRC, **xs}, script=__file__, probe=probe,
                            notes="New-claim reading (draft update_20261007_shorts_02): Monday with "
                                  "the bias, Tuesday against; Thursday-only trade, clustered by week.")
        print(" ", p)
