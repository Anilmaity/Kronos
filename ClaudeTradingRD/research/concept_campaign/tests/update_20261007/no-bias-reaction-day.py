"""no-bias-reaction-day -- update_20261007_live_07 (trade_test, TTrades voice, 9YVBe-20Hdg).

Claim: on a no-bias day (daily inside an inside candle, market waiting for FOMC) it is "a
reaction game": wait for the 09:30-09:45 15m candle ("9:45 cuz that gives us a 15-minute candle
that's formed. And that usually tells us what happens"), then scalp ~2R on the 1m, "not trying
to hold for a huge expansion".

Declared before run (no parameter search):
  * day = 18:00 NY roll; completed days need >= 600 M1 bars (stub sessions skipped)
  * "today inside" = today's range 18:00 -> 09:45 NY lies within the previous day's high/low
    (the live daily is incomplete at 09:45, so "inside so far" is what he could see)
  * reading u1007a (structural no-bias): previous day inside the day before it AND today inside
    so far ("We have candle. We're inside that candle and then we're inside that candle")
  * reading u1007b (pre-FOMC no-bias): scheduled FOMC statement day AND today inside so far
  * reaction direction = direction of the 09:30-09:45 NY 15m candle (close vs open; doji dropped).
    The correlated-asset read (ES/NQ/YM SMT) needs data we lack; gold's own 15m reaction is the
    only reaction available on M1 XAUUSD.
  * entry = first M1 open at/after 09:45; stop = the 15m candle's opposite extreme (its protected
    swing); target 2R; max hold 240 min (exit by 13:45, before the 14:00 FOMC statement; scalp,
    no holding for expansion)

AUDIT 2026-10-07 (vault re-run): FOMC calendar switched from time_own_02b/_common.py (ends
2026-03-18, so in-span statement days 2026-04-29 / 2026-06-17 read as "not FOMC" -- trap 7,
"never evaluated" looking like "failed") to time_own_03b/_common.py (every scheduled statement
day 2016-2026, transcribed from federalreserve.gov, declared before that batch ran). Same
hypothesis, same readings; nothing else changed.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_own_03b")
import numpy as np
import pandas as pd
import concept_lab as cl
from _common import FOMC

CID = "no-bias-reaction-day"
TZ = "America/New_York"
O, E = 9 * 60 + 30, 9 * 60 + 45
FOMC_D = set(pd.DatetimeIndex(FOMC).normalize())


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    ny = m1.index.tz_convert(TZ)
    mod = np.asarray(ny.hour * 60 + ny.minute)
    tday = (ny.tz_localize(None) + pd.Timedelta(hours=6)).normalize()     # 18:00 roll
    g = m1.groupby(tday)
    day = pd.DataFrame({"h": g["high"].max(), "l": g["low"].min(), "n": g["close"].size()})
    full = day[day["n"] >= 600]
    pre = (mod < E) | (mod >= 18 * 60)
    gp = m1[pre].groupby(tday[pre])
    sofar = pd.DataFrame({"h": gp["high"].max(), "l": gp["low"].min()})
    c15 = (mod >= O) & (mod < E)
    gc = m1[c15].groupby(tday[c15])
    cnd = pd.DataFrame({"o": gc["open"].first(), "h": gc["high"].max(), "l": gc["low"].min(),
                        "c": gc["close"].last(), "n": gc["close"].size()})
    cnd = cnd[(cnd["n"] >= 10) & (cnd.index.dayofweek < 5)]
    rows = []
    fi = full.index
    for d, r in cnd.iterrows():
        k = fi.searchsorted(d) - 1                 # previous completed day
        if k < 1 or d not in sofar.index:
            continue
        p, pp = full.iloc[k], full.iloc[k - 1]
        s = sofar.loc[d]
        today_in = (s.h <= p.h) and (s.l >= p.l)
        prev_in = (p.h <= pp.h) and (p.l >= pp.l)
        dirn = np.sign(r.c - r.o)
        if dirn == 0 or not today_in:
            continue
        t = (pd.Timestamp(d).tz_localize(TZ) + pd.Timedelta(minutes=E)).tz_convert("UTC")
        rows.append((t, t, int(dirn), r.l if dirn > 0 else r.h, 2.0, bool(prev_in), d in FOMC_D))
    out = pd.DataFrame(rows, columns=["decision_time", "available_at", "direction", "stop_px",
                                      "rr", "prev_inside", "fomc"])
    return out


def det_a(m1):
    x = detect(m1)
    return x[x["prev_inside"]].reset_index(drop=True)


def det_b(m1):
    x = detect(m1)
    return x[x["fomc"]].reset_index(drop=True)


PARAMS = {"day_roll": "18:00 NY", "min_m1_day": 600, "reaction_candle": "15m 09:30-09:45 NY",
          "direction": "15m candle close vs open", "stop": "15m candle opposite extreme",
          "rr": 2.0, "max_hold": "240min", "today_inside": "18:00->09:45 range within prior day H/L"}
SRC = {"day_roll": "method_spec: README trap 8, day rolls 18:00 NY",
       "min_m1_day": "method_spec: README trap 6, skip stub sessions",
       "reaction_candle": "corpus: 9YVBe-20Hdg '9:45 cuz that gives us a 15-minute candle that's formed. And that usually tells us what happens'",
       "direction": "declared-before-run: 'it's just a reaction game' -- correlated-asset read unavailable; gold's own 15m reaction used",
       "stop": "corpus: 9YVBe-20Hdg 'I put my stop loss on the protected swing' -> the formed 15m candle's opposite extreme",
       "rr": "corpus: 9YVBe-20Hdg 'You get two R ... if you want to trade the one minute and scalp things'",
       "max_hold": "corpus: 9YVBe-20Hdg 'you're not trying to hold for a huge expansion'; declared-before-run: flat by 13:45, before the 14:00 FOMC statement",
       "today_inside": "corpus: 9YVBe-20Hdg 'we're inside day. So inside day inside day pretty much just a consolidation'"}

READINGS = {
    "u1007a": (det_a, "prev_inside", "no-bias = previous day inside the day before AND today (18:00->09:45) inside previous day",
               "corpus: 9YVBe-20Hdg 'We have candle. We're inside that candle and then we're inside that candle. So that's just consolidation'"),
    "u1007b": (det_b, "fomc", "no-bias = scheduled FOMC statement day AND today (18:00->09:45) inside previous day",
               "corpus: 9YVBe-20Hdg 'I think the market's just waiting for the rate announcement' / 'I don't really have a bias today ... the market's waiting for a Fed rate'; calendar declared-before-run in time_own_03b/_common.py (federalreserve.gov fomccalendars, every scheduled statement day 2016-2026)"),
}

if __name__ == "__main__":
    full = cl.cache_frame("u1007_nobias_react_v2_fomc03b", lambda: detect(cl.load_m1()))
    print(len(full), "inside-so-far days; prev_inside", int(full.prev_inside.sum()), "fomc", int(full.fomc.sum()))
    for reading, (det, col, rule, src_rule) in READINGS.items():
        ev = full[full[col]].reset_index(drop=True)
        probe = cl.probe_lookahead(det, ev, lookback="20D")
        res = cl.trade_test(ev, max_hold="240min", claim="+")
        op = {"rules": [rule,
                        "decision 09:45 NY after the 09:30-09:45 15m candle closes; direction = that candle's colour (doji dropped)",
                        "entry next M1 open; stop at the 15m candle's opposite extreme; target 2R; max hold 240 min",
                        "control = harness matched random entry (same direction/stop/target geometry, +/-30 d)"],
              "params": {**PARAMS, "no_bias_rule": rule}}
        src = {**SRC, "no_bias_rule": src_rule}
        kw = dict(operationalization=op, params_source=src, script=__file__, probe=probe,
                  notes="Correlated-asset reaction (ES/NQ/YM) not available; gold's own 15m candle stands in. FOMC calendar: time_own_03b (complete through 2026-07-29; audit fix, was time_own_02b ending 2026-03-18).")
        try:
            p = cl.write_result(CID, reading, res, **kw)
        except Exception as e:  # new update concept not yet in batches.json
            print("write_result refused:", e)
            p = cl.write_result(CID, reading, res, allow_unknown_id=True, **kw)
        print(reading, p)
        for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars"):
            print("  ", k, res.get(k))
