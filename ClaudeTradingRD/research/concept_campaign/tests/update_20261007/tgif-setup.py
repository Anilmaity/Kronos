"""tgif-setup — update_20261007_live_05 (TTrades, 4rNC3QXxC20). NEW claim only:
a mid-week consolidation day disqualifies TGIF ("it's three days of expansion"), and the Friday
entry needs a previous-day-low sweep traded back in (no overnight entry on an assumed extreme).

Baseline book (both arms), bearish week -> long Friday (bullish mirrored):
  * Mon..Thu high formed Monday or Tuesday; Thursday is an expansion day and makes the
    Mon..Thu low ("expansion through Thursday");
  * weekly objective hit by Thursday: the Mon..Thu low reached the PREVIOUS WEEK'S LOW
    (same definition as the 2026-09-23 readings a/b, method spec §5.2). AUDIT 2026-10-07: the
    first run dropped this, citing "I could say, yeah, we hit this low" as "left open"; the
    source lists it as the third requirement ("Last thing, it's weekly objective") and the
    method spec defines TGIF as a week "whose weekly objective has been hit";
  * Friday session (Thu 18:00 NY -> Fri 17:00 NY): the first 1h bar that, after price has
    traded below Thursday's low, closes back above it -> long at the next M1 open;
  * stop = Friday low so far (the sweep extreme); target = week low + 0.25 x week range
    (library 20-30% band midpoint); exit Friday 17:00 NY (trading minutes).
  * expansion day (bearish) = close < open AND low < previous day's low; else consolidation.
Gate (claim '+': gated better):
  u1007a: Tue, Wed and Thu are ALL expansion days (any Tue-Thu consolidation disqualifies);
  u1007b: Wednesday is an expansion day (only a Wednesday consolidation disqualifies).
Dropped: SMT, as optional confluence ("usually I want ... and have SMT"; draft "ideally"). That
is a reading choice, not a data limit: XAG H1 exists and other campaign scripts use it.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_03a")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                                # noqa: E402
from _common import daily_frame, friday_close_utc, trading_minutes     # noqa: E402

CID = "tgif-setup"
RETR = 0.25
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold",
        "week", "gate_at", "all3_exp", "wed_exp"]


def _exp(day, prev, s):
    """Expansion day in the week's direction s (+1 bullish week, -1 bearish week)."""
    if s > 0:
        return bool(day["close"] > day["open"] and day["high"] > prev["high"])
    return bool(day["close"] < day["open"] and day["low"] < prev["low"])


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily_frame(m1)
    if len(d) < 5:
        return pd.DataFrame(columns=COLS)
    h1 = cl.build_bars(m1, "1h")
    rows = []
    prev = None                                      # (week, high, low) of the previous week
    for wk, w in d.groupby("week", sort=True):
        pw, prev = prev, (wk, w["high"].max(), w["low"].min())
        if pw is None or (wk - pw[0]) != pd.Timedelta(days=7):
            continue                                 # no previous week -> objective unknown
        mt = w[w["wd"] <= 3]
        if list(mt["wd"]) != [0, 1, 2, 3]:
            continue
        mon, tue, wed, thu = (mt.iloc[i] for i in range(4))
        hi_day = int(np.argmax(mt["high"].to_numpy()))
        lo_day = int(np.argmin(mt["low"].to_numpy()))
        if hi_day in (0, 1) and lo_day == 3:
            s = -1                                   # bearish week -> long TGIF
        elif lo_day in (0, 1) and hi_day == 3:
            s = 1                                    # bullish week -> short TGIF
        else:
            continue
        if not (mt["low"].min() <= pw[2] if s < 0 else mt["high"].max() >= pw[1]):
            continue                                 # weekly objective not hit by Thursday
        if not _exp(thu, wed, s):
            continue
        e_tue, e_wed = _exp(tue, mon, s), _exp(wed, tue, s)
        f0, f1 = pd.Timestamp(thu["close_time"]), friday_close_utc(wk)
        fr = h1[(h1["close_time"] > f0) & (h1["close_time"] <= f1)]
        if fr.empty:
            continue
        lvl = thu["low"] if s < 0 else thu["high"]
        ext = fr["low"].cummin() if s < 0 else fr["high"].cummax()
        swept = (ext < lvl) if s < 0 else (ext > lvl)
        back = (fr["close"] > lvl) if s < 0 else (fr["close"] < lvl)
        hit = fr[swept & back]
        if hit.empty:
            continue
        b = hit.iloc[0]
        x = float(ext.loc[b.name])
        whi = max(mt["high"].max(), float(fr.loc[:b.name, "high"].max()))
        wlo = min(mt["low"].min(), float(fr.loc[:b.name, "low"].min()))
        tgt = wlo + RETR * (whi - wlo) if s < 0 else whi - RETR * (whi - wlo)
        if (s < 0 and tgt <= b["close"]) or (s > 0 and tgt >= b["close"]):
            continue                                 # already at/through the target
        dec = pd.Timestamp(b["close_time"])
        hold = trading_minutes(dec, f1)
        if hold <= pd.Timedelta(0):
            continue
        rows.append({"decision_time": dec, "available_at": dec, "direction": -s,
                     "stop_px": x, "target_px": float(tgt), "max_hold": hold,
                     "week": str(pd.Timestamp(wk).date()), "gate_at": f0,
                     "all3_exp": bool(e_tue and e_wed), "wed_exp": bool(e_wed)})
    return pd.DataFrame(rows, columns=COLS)


SRC = {"extreme_days": "corpus: 4rNC3QXxC20 'It' be Monday, Tuesday high. Do we have that? Yeah'",
       "thursday_expansion": "corpus: 4rNC3QXxC20 'Expansion through Thursday' / 'Thursday sure "
                             "expands'; Thursday makes the Mon..Thu extreme declared-before-run",
       "expansion_day": "declared-before-run: no threshold in source; expansion = close in the "
                        "week's direction AND beyond the previous day's extreme, else consolidation",
       "gate": "corpus: 4rNC3QXxC20 'Wednesday's a consolidation ... No, it's three days of "
               "expansion. Multiple days expansion' (a: any Tue-Thu, b: Wednesday only — the "
               "draft's stated ambiguity)",
       "friday_entry": "corpus: 4rNC3QXxC20 'Normally, I like to see a sweep of the previous day "
                       "low, then trading that back in' / 'So, we go to the hourly' -> first 1h "
                       "close back inside Thursday's extreme after a sweep",
       "no_overnight_assumption": "corpus: 4rNC3QXxC20 'the only way ... would have been overnight, "
                                  "assuming that this formed the low of the week. I don't really "
                                  "trust that' -> no entry without a prior PDL sweep",
       "stop": "declared-before-run: the Friday sweep extreme (the invalidation of 'trading that "
               "back in')",
       "retracement": "corpus: _CSO5Mf7CM8 'a retracement of 20 to 30% of the weekly range' — "
                      "midpoint 0.25 (same as prior readings a/b)",
       "exit": "corpus: 4rNC3QXxC20 'It's trading the weekly candle' -> Friday trade, exit Friday "
               "17:00 NY",
       "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
       "min_coverage": "declared-before-run: drop stub sessions (README trap 6)",
       "hold_basis": "declared-before-run: Friday exit in trading minutes (README trap 7)",
       "smt": "corpus: 4rNC3QXxC20 'usually I want to frame that off the previous day low and "
              "have SMT' (draft: 'ideally with SMT'; library ambiguity: SMT required vs "
              "confluence unsettled) -> read as optional confluence and dropped. Not a data "
              "limit: XAG H1 exists (vault trap 7)",
       "objective": "corpus: 4rNC3QXxC20 'Last thing, it's weekly objective' (a stated TGIF "
                    "requirement) + method_spec: §2.5 TGIF = classic-expansion week 'whose weekly "
                    "objective has been hit'; §5.2 previous-period extreme -> previous week's "
                    "low (bearish week) / high reached Mon..Thu, as in readings a/b"}
PARAMS = {"extreme_days": "Mon,Tue", "thursday_expansion": "Thu expansion day making Mon..Thu extreme",
          "expansion_day": "close beyond open AND beyond prior day extreme",
          "friday_entry": "first 1h close back inside Thu low/high after sweep",
          "no_overnight_assumption": "sweep required", "stop": "Friday sweep extreme",
          "retracement": RETR, "exit": "Friday 17:00 NY", "day_open_hour": 18,
          "min_coverage": 0.5, "hold_basis": "bars", "smt": "dropped (optional confluence)",
          "objective": "previous week's low (bearish week) / high reached Mon..Thu"}
RULES = ["week: Mon/Tue extreme, Thursday expansion day making the opposite Mon..Thu extreme",
         "weekly objective: Mon..Thu low <= previous week's low (bearish week; mirrored)",
         "Friday: 1h sweep of Thursday's low (bearish week) then first 1h close back above -> "
         "long next M1 open; stop at sweep low; target week low + 0.25 x range; exit Fri 17:00 NY",
         "mirrored for bullish weeks"]
READINGS = {"u1007a": ("all3_exp", "gate = Tue, Wed, Thu all expansion days"),
            "u1007b": ("wed_exp", "gate = Wednesday expansion day")}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_u1007_v2_objective", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict(),
          ev["all3_exp"].sum(), ev["wed_exp"].sum())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    for rd, (col, g) in READINGS.items():
        res = cl.gate_test(ev, col, mask_available_at="gate_at", hold_basis="bars",
                           cluster="week")
        for k in ("n", "n_gated", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "ties"):
            print(" ", rd, k, res.get(k))
        p = cl.write_result(CID, rd, res,
                            operationalization={"rules": RULES + [g], "params": PARAMS},
                            params_source=SRC, script=__file__, probe=probe,
                            notes="Gate test of the new claim only (consolidation day "
                                  "disqualifies), on TGIF-qualified weeks (Mon/Tue extreme, "
                                  "Thursday expansion, weekly objective hit); SMT dropped as "
                                  "optional confluence. Clustered by week; hold_basis='bars'. "
                                  "AUDIT 2026-10-07: first run omitted the weekly objective.")
        print(p)
