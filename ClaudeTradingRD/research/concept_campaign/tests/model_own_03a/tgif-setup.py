"""tgif-setup — TGIF Setup, TTrades own voice. CONTESTED (Friday-reversal vs Thursday-reversal).

Shared week qualification (bullish week -> the TGIF trade is SHORT; bearish mirrored):
  * the week's low (Mon..Thu) formed on Monday or Tuesday;
  * expansion after it: Wednesday closed up (close > open);
  * the weekly objective was hit by Thursday's close: the week's high (Mon..Thu) reached the
    PREVIOUS WEEK'S HIGH (previous-period extreme = the first target class, method spec §5.2);
  * target = 25% retracement of the weekly range from the week's extreme (the 20-30% band's
    midpoint); stop = the reversal extreme; hold to Friday 17:00 NY (trading minutes).
Reading a — Friday forms the reversal: Thursday also closed up and is NOT a bearish C2; on
  Friday, price takes Thursday's high and a bearish 1h CISD confirms (first one on Friday
  whose swing extreme is above Thursday's high); entry at that 1h close.
Reading b — Thursday is the reversal (the "not picture perfect" Short _-aPdmLe6zw): Thursday
  is a bearish daily C2 closure (high > Wednesday high, close < Wednesday high) with a bearish
  hourly CISD inside it; entry at the Friday session open; stop at Thursday's high.
trade_test, claim '+'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                            # noqa: E402
from detectors.cisd import cisd_events                              # noqa: E402
from _common import (daily_frame, c2_flags, h1_cisd, friday_close_utc,  # noqa: E402
                     trading_minutes)

CID = "tgif-setup"
RETR = 0.25
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold",
        "week"]


def _weeks(d: pd.DataFrame):
    """Yield (week, Mon..Thu frame, Friday row or None, previous week's high/low)."""
    g = list(d.groupby("week", sort=True))
    prev = None
    for wk, w in g:
        hi, lo = w["high"].max(), w["low"].min()
        if prev is not None and (wk - prev[0]) == pd.Timedelta(days=7):
            yield wk, w, prev[1], prev[2]
        prev = (wk, hi, lo)


def _qualify(w: pd.DataFrame, pwh: float, pwl: float):
    """Week shape through Thursday. Returns trade direction (-1 short after a bullish week,
    +1 long after a bearish week) or 0."""
    mt = w[w["wd"] <= 3]
    if set(mt["wd"]) != {0, 1, 2, 3}:
        return 0, mt
    wed, thu = mt[mt["wd"] == 2].iloc[0], mt[mt["wd"] == 3].iloc[0]
    lo_day = int(mt["wd"].iloc[int(np.argmin(mt["low"].to_numpy()))])
    hi_day = int(mt["wd"].iloc[int(np.argmax(mt["high"].to_numpy()))])
    if lo_day in (0, 1) and wed["close"] > wed["open"] and mt["high"].max() >= pwh:
        return -1, mt
    if hi_day in (0, 1) and wed["close"] < wed["open"] and mt["low"].min() <= pwl:
        return 1, mt
    return 0, mt


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily_frame(m1)
    h1 = cl.build_bars(m1, "1h")
    if len(d) < 10:
        return pd.DataFrame(columns=COLS)
    bull, bear = c2_flags(d)
    pos = {t: k for k, t in enumerate(d.index)}
    cis = cisd_events(h1[["open", "high", "low", "close"]], level_rule="series_open",
                      left=2, right=2, max_wait=3)
    rows = []
    for wk, w, pwh, pwl in _weeks(d):
        s, mt = _qualify(w, pwh, pwl)
        if s == 0:
            continue
        thu = mt[mt["wd"] == 3].iloc[0]
        k = pos[thu.name]
        if s < 0 and not (thu["close"] > thu["open"] and not bear[k]):
            continue
        if s > 0 and not (thu["close"] < thu["open"] and not bull[k]):
            continue
        # Friday session = from Thursday's close to Friday 17:00 NY. Not read from the
        # Friday daily row: a partial Friday is a "stub" until it completes (probe fix).
        f0, f1 = pd.Timestamp(thu["close_time"]), friday_close_utc(wk)
        want = "bearish" if s < 0 else "bullish"
        c = cis[(cis["direction"] == want) & (cis["extreme_time"] >= f0)
                & (cis["confirm_time"] >= f0) & (cis["confirm_time"] < f1)]
        c = c[c["extreme_price"] > thu["high"]] if s < 0 else c[c["extreme_price"] < thu["low"]]
        if c.empty:
            continue
        e = c.iloc[0]
        dec = pd.Timestamp(h1.loc[e["confirm_time"], "close_time"])
        upto = h1[(h1.index >= f0) & (h1.index <= e["confirm_time"])]
        whi = max(mt["high"].max(), upto["high"].max())
        wlo = min(mt["low"].min(), upto["low"].min())
        tgt = whi - RETR * (whi - wlo) if s < 0 else wlo + RETR * (whi - wlo)
        hold = trading_minutes(dec, friday_close_utc(wk))
        if hold <= pd.Timedelta(0):
            continue
        rows.append({"decision_time": dec, "available_at": dec, "direction": s,
                     "stop_px": float(e["protected_swing"]), "target_px": float(tgt),
                     "max_hold": hold, "week": str(pd.Timestamp(wk).date())})
    return pd.DataFrame(rows, columns=COLS)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily_frame(m1)
    h1 = cl.build_bars(m1, "1h")
    if len(d) < 10:
        return pd.DataFrame(columns=COLS)
    bull, bear = c2_flags(d)
    pos = {t: k for k, t in enumerate(d.index)}
    rows = []
    for wk, w, pwh, pwl in _weeks(d):
        s, mt = _qualify(w, pwh, pwl)
        if s == 0:
            continue
        thu = mt[mt["wd"] == 3].iloc[0]
        k = pos[thu.name]
        if s < 0 and not bear[k]:
            continue
        if s > 0 and not bull[k]:
            continue
        if h1_cisd(h1, thu.name, thu["close_time"], "bearish" if s < 0 else "bullish") is None:
            continue
        dec = pd.Timestamp(thu["close_time"])
        whi, wlo = mt["high"].max(), mt["low"].min()
        tgt = whi - RETR * (whi - wlo) if s < 0 else wlo + RETR * (whi - wlo)
        hold = trading_minutes(dec, friday_close_utc(wk))
        if hold <= pd.Timedelta(0):
            continue
        rows.append({"decision_time": dec, "available_at": dec, "direction": s,
                     "stop_px": float(thu["high"] if s < 0 else thu["low"]),
                     "target_px": float(tgt), "max_hold": hold,
                     "week": str(pd.Timestamp(wk).date())})
    return pd.DataFrame(rows, columns=COLS)


SRC = {"extreme_days": "corpus: _CSO5Mf7CM8 / method_spec §2.5 — weekly extreme formed Monday "
                       "or Tuesday",
       "expansion": "declared-before-run: 'expansion through Wednesday and Thursday' = up-close "
                    "(bullish week) daily candles; no threshold is given",
       "objective": "method_spec: §5.2 targets — previous candles' unswept extremes first; "
                    "the weekly objective is taken as the previous week's high (bullish week)",
       "retracement": "corpus: _CSO5Mf7CM8 'a retracement of 20 to 30% of the weekly range' — "
                      "band midpoint 0.25 declared-before-run",
       "cisd_level_rule": "method_spec: §4.2 first-candle-open default",
       "cisd_swing": "phase3: conjunction preregistration locked CISD config (2/2 swing, "
                     "max_wait 3)",
       "cisd_scope": "method_spec: §2.4 [P] scope default 'range'",
       "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
       "min_coverage": "declared-before-run: drop stub sessions (README trap 6)",
       "exit": "corpus: hTsltdflraY — TGIF is a Friday trade back into the weekly range; hold "
               "to Friday 17:00 NY",
       "hold_basis": "declared-before-run: Friday exit in trading minutes (README trap 7)"}
PARAMS = {"extreme_days": "Mon,Tue", "expansion": "Wed up-close (a: Thu up-close too)",
          "objective": "previous week's high/low reached Mon..Thu", "retracement": RETR,
          "cisd_level_rule": "series_open", "cisd_swing": "2/2, max_wait 3 (1h)",
          "cisd_scope": "range", "day_open_hour": 18, "min_coverage": 0.5,
          "exit": "Friday 17:00 NY", "hold_basis": "bars"}
READINGS = {
    "a": (detect_a, {"rules": [
        "week qualifies: Mon/Tue extreme, Wed and Thu expansion closes, previous week's "
        "extreme reached by Thursday, Thursday not a counter C2",
        "Friday: price takes Thursday's high (bullish week) and the first bearish 1h CISD "
        "whose swing extreme is above it confirms -> short at the next M1 open",
        "stop at the CISD's protected swing; target = week high - 0.25 x week range; hold to "
        "Friday 17:00 NY"], "params": PARAMS}, None),
    "b": (detect_b, {"rules": [
        "week qualifies: Mon/Tue extreme, Wed expansion close, previous week's extreme "
        "reached by Thursday",
        "Thursday = counter daily C2 closure with a counter hourly CISD inside it",
        "short at the Friday session open (bullish week); stop at Thursday's high; target = "
        "week high - 0.25 x week range; hold to Friday 17:00 NY"],
        "params": {**PARAMS, "expansion": "Wed up-close", "cisd_swing": "n/a (in-candle)"}},
        None),
}

if __name__ == "__main__":
    for rd, (fn, op, _) in READINGS.items():
        ev = cl.cache_frame(f"{CID}_{rd}_v1", lambda: fn(cl.load_m1()))
        print(rd, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(fn, ev, lookback="30D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, hold_basis="bars", cluster="week")
        for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "exposure_bars", "ctrl_overlap", "ties"):
            print(" ", k, res.get(k))
        src = dict(SRC)
        if rd == "b":
            src["cisd_swing"] = "method_spec: §2.4 step 3 in-candle hourly CISD (no swing knob)"
        p = cl.write_result(CID, rd, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe,
                            notes="Weekly trades clustered by week id; Friday exit in trading "
                                  "minutes (hold_basis='bars').")
        print(p)
