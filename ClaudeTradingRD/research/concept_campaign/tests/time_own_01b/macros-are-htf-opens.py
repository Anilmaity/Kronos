"""macros-are-htf-opens — a 'macro' is only the opening of new higher-timeframe candles.

Contested concept; two readings, both declared before the first run.

Reading a (rate_test, claim '+'): "10:00 = a new 30-minute, hourly and 4-hour candle
all open together ... Treat these as the points at which price can change direction,
10:00 being the stronger" (detection rules 4-5; measurable: "frequency of intraday
direction change at 9:45 and 10:00 vs other quarter-hours").
  * per NY weekday: pre = close(09:59 M1) - open(09:30 M1); post = close(10:29 M1) -
    open(10:00 M1) (30-minute legs = the smallest of the HTF candles named at 10:00).
  * hit = sign(pre) != sign(post) (a direction change at the pivot); rows with a
    zero leg or a missing M1 bar are dropped.
  * null (geometry-matched: same 30/30-minute legs, same day): the same statistic at a
    random OTHER quarter-hour pivot of the same morning, 08:00..11:45 NY excluding
    09:45 and 10:00 (the two HTF-open pivots the concept names).
  * pure clock predictor -> no_detector.

Reading b (gate_test, claim '+'): "He will not enter at 9:50, near the end of a
15-minute candle; he waits for the next candle open" / "Do not enter late inside a
forming candle; wait for the next candle open."
  * baseline: phase-3 rung-0 5m CISD book, all day (decide at the confirming 5m
    close, enter next M1 open, stop protected swing, 2R, hold 10 bars = 50 min).
  * gate: the decision (= entry) falls exactly on a 15-minute candle open
    (NY minute % 15 == 0) vs mid-candle (5 or 10 minutes into the 15m candle).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (cl, np, pd, cisd_book, ny_mod, ny_dates, at_ny,  # noqa: E402
                     bar_pos_exact, PHASE3_SRC)

CID = "macros-are-htf-opens"
PIVOT = "10:00"
LEG = 30
NULL_PIVOTS = [f"{h:02d}:{m:02d}" for h in range(8, 12) for m in (0, 15, 30, 45)
               if f"{h:02d}:{m:02d}" not in ("09:45", "10:00")]


def pivot_change(m1, dates, hhmm, leg=LEG):
    mkt = cl.get_market(m1)
    p0 = at_ny(dates, hhmm)
    a = bar_pos_exact(m1, p0 - pd.Timedelta(minutes=leg))
    b = bar_pos_exact(m1, p0 - pd.Timedelta(minutes=1))
    c = bar_pos_exact(m1, p0)
    d = bar_pos_exact(m1, p0 + pd.Timedelta(minutes=leg - 1))
    ok = (a >= 0) & (b >= 0) & (c >= 0) & (d >= 0)
    pre = np.where(ok, mkt.c[b] - mkt.o[a], np.nan)
    post = np.where(ok, mkt.c[d] - mkt.o[c], np.nan)
    out = np.where(np.isfinite(pre) & np.isfinite(post) & (pre != 0) & (post != 0),
                   (np.sign(pre) != np.sign(post)).astype(float), np.nan)
    return p0, out


def reading_a():
    m1 = cl.load_m1()
    dates = ny_dates(m1)
    t, obs = pivot_change(m1, dates, PIVOT)
    keep = np.isfinite(obs) & ~pd.isna(t)
    dates, t, obs = dates[keep], t[keep], obs[keep]
    mat = np.column_stack([pivot_change(m1, dates, q)[1] for q in NULL_PIVOTS])

    def null_fn(rng, k):
        j = rng.integers(0, mat.shape[1], len(obs))
        return mat[np.arange(len(obs)), j]

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="+")
    op = {"rules": [
        "per NY weekday, pivot 10:00 NY (DST-aware)",
        "pre leg = close(09:59 M1) - open(09:30 M1); post leg = close(10:29 M1) - "
        "open(10:00 M1); hit = the two legs have opposite signs (direction change)",
        "null = same statistic at a random other quarter-hour pivot of the same "
        "morning (08:00-11:45 NY, excluding 09:45 and 10:00)",
        "rows with a missing M1 bar or a zero leg dropped"],
        "params": {"pivot": PIVOT, "leg_min": LEG, "null_pivots": NULL_PIVOTS}}
    src = {"pivot": "corpus: yNgx9OAefuI '10 is where we get a new 4hour candle'; "
                    "m0wTBdUe7gs 'when becomes the time where something can adjust, usually 10'",
           "leg_min": "declared-before-run: 30 minutes = the smallest HTF candle "
                      "(30m) the concept names as opening at 10:00",
           "null_pivots": "corpus: measurable 'direction change at 9:45 and 10:00 vs "
                          "other quarter-hours'; declared-before-run: the NY morning "
                          "08:00-12:00 quarter-hours"}
    return res, op, src


def detect_b(m1):
    ev = cisd_book(m1, "5min")
    ev["at_15m_open"] = (ny_mod(ev["decision_time"]) % 15 == 0) if len(ev) else \
        pd.Series(dtype=bool)
    return ev


def reading_b():
    ev = cl.cache_frame("cisd5m_at15open", lambda: detect_b(cl.load_m1()))
    print("events", len(ev), "gated share", float(ev["at_15m_open"].mean()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "at_15m_open", mask_available_at="decision_time",
                       max_hold="50min", claim="+")
    op = {"rules": [
        "baseline: phase-3 rung-0 5m CISD (series_open, 2/2, max_wait 3, min_series 1), "
        "all day; decide at the confirming 5m close; enter next M1 open; stop protected "
        "swing; 2R; hold 50 min (10 bars)",
        "gate: decision/entry exactly at a 15-minute candle open (NY minute % 15 == 0) "
        "vs 5 or 10 minutes into a forming 15m candle"],
        "params": {"tf": "5min", "max_hold": "50min", "rr": 2.0, "gate_candle": "15min"}}
    src = {"tf": PHASE3_SRC, "max_hold": PHASE3_SRC, "rr": PHASE3_SRC,
           "gate_candle": "corpus: macros-are-htf-opens variant 'He will not enter at "
                          "9:50, near the end of a 15-minute candle; he waits for the "
                          "next candle open'"}
    return res, op, src, probe


def show(res):
    print({k: res.get(k) for k in ("n", "n_gated", "observed_rate", "null_rate", "avg_R",
                                   "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                                   "verdict_detail", "ties", "ctrl_overlap", "halves",
                                   "gate_rate", "exposure_bars")})


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        res, op, src = reading_a()
        show(res)
        print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                              script=__file__,
                              no_detector="pure clock rule: the 10:00 NY pivot and the "
                                          "null quarter-hours are fixed wall-clock times",
                              notes="Reading a: is 10:00 NY (HTF candle opens) a point of "
                                    "direction change more often than other NY-morning "
                                    "quarter-hours? Gold is not an index; the corpus's "
                                    "10:00 4H open is the futures grid, on the forex grid "
                                    "10:00 opens 1h/30m/15m only."))
    if "b" in which:
        res, op, src, probe = reading_b()
        show(res)
        print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                              script=__file__, probe=probe,
                              notes="Reading b: 'wait for the next candle open' as a gate "
                                    "on the 5m CISD book: entries on a 15m open vs "
                                    "mid-candle."))
