"""new-york-intraday-time-levels — 08:00/08:30 reverse, 09:30-10:00 expands, 10:00 completes.

Contested concept; two readings, declared before the first run.

Reading a (trade_test, claim '+') — the "8 a.m. reversal sequence" Short (8fseTcJMiBo):
"I'm going to want to see a candle 2 closure at 8:00 [on the HOURLY] ... This allows me
to anticipate the 9 to 10 a.m. candle to expand"; stop "on that low"; 10:00 = final TP.
  * 1h bars on the hour (18:00 NY day roll). C1 = the 07:00 NY hourly candle, C2 = the
    08:00 NY hourly candle (must follow C1 by exactly 1h).
  * bullish C2 closure: C2.low < C1.low and C2.close >= C1.low (and C2 did not also
    sweep C1.high); bearish mirrored (detectors.primitives C1/C2 definition).
  * decide at the 08:00 candle's close (09:00 NY); enter next M1 open in the reversal
    direction; stop = C2's swept extreme; no price target; time exit at 10:00 NY
    (max_hold 60 min) - the 9-to-10 candle is expected to expand.
  * control holds the NY clock (ctrl_tod_tol_min=30): the question is whether the
    08:00 C2 picks the 9-10 direction, not whether 9-10 is volatile (trap 9).
  * simplification: his LTF CISD + pre-09:30 continuation entry is replaced by the
    09:00 open entry with the C2 extreme as the stop.

Reading b (rate_test, claim '+') — "10:00: the day's high or low frequently completes
here"; "09:30-10:00 - the volatility window; the move is expected to complete inside it"
(measurable: distribution of the day's extreme timestamp across 09:30 / 09:45 / 10:00).
  * per trading day (18:00 NY roll, >= 1,200 M1 bars): hit = the day's high OR low
    (first M1 bar printing it) starts inside [09:30, 10:00) NY.
  * null (same window length, same day): a random 30-minute wall-clock window starting
    at a random M1 bar of the same trading day that ends by the day's last bar.
  * pure clock predictor -> no_detector.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ny_mod, utc_ns, empty  # noqa: E402
from concept_lab.data import trading_day  # noqa: E402

CID = "new-york-intraday-time-levels"
C1_H, C2_H = 7, 8
HOLD = "60min"
WIN = (9 * 60 + 30, 10 * 60)
MIN_DAY_BARS = 1200


def detect_a(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    b = cl.build_bars(m1, "1h")
    if len(b) < 3:
        return empty(cols)
    st = pd.DatetimeIndex(b.index)
    mod = ny_mod(st)
    i2 = np.flatnonzero(mod == C2_H * 60)
    i2 = i2[i2 >= 1]
    i1 = i2 - 1
    ok = (st[i2] - st[i1]) == pd.Timedelta(hours=1)
    ok &= mod[i1] == C1_H * 60
    i1, i2 = i1[ok], i2[ok]
    h1, l1 = b["high"].to_numpy()[i1], b["low"].to_numpy()[i1]
    h2, l2, c2 = (b["high"].to_numpy()[i2], b["low"].to_numpy()[i2],
                  b["close"].to_numpy()[i2])
    bull = (l2 < l1) & (c2 >= l1)
    bear = (h2 > h1) & (c2 <= h1)
    one = bull ^ bear
    i2, bull, l2, h2 = i2[one], bull[one], l2[one], h2[one]
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[i2])
    out = pd.DataFrame({"decision_time": ct, "available_at": ct,
                        "direction": np.where(bull, 1, -1),
                        "stop_px": np.where(bull, l2, h2).astype(float),
                        "target_px": np.nan})
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


def reading_a():
    ev = cl.cache_frame("ny8am_c2_1h", lambda: detect_a(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=HOLD, claim="+", ctrl_tod_tol_min=30)
    op = {"rules": [
        "1h bars on the hour, 18:00 NY roll; C1 = 07:00 NY hourly, C2 = 08:00 NY hourly",
        "bullish C2 closure: C2.low < C1.low and C2.close >= C1.low (not also sweeping "
        "C1.high); bearish mirrored",
        "decide at 09:00 NY (C2 close); enter next M1 open in the reversal direction; "
        "stop = C2 swept extreme; no target; exit at 10:00 NY (60 min)",
        "control: same direction/stop distance/hold at the same NY clock (+/-30 min) "
        "on other days within +/-30 days"],
        "params": {"c2_hour": "08:00", "c1_hour": "07:00", "max_hold": HOLD,
                   "target": "none (time exit 10:00)", "ctrl_tod_tol_min": 30}}
    src = {"c2_hour": "corpus: 8fseTcJMiBo 'I'm going to want to see a candle to closure "
                      "at 8:00'",
           "c1_hour": "corpus: 8fseTcJMiBo candle 2 closure on the HOURLY chart (C1 = the "
                      "preceding hourly candle)",
           "max_hold": "corpus: 8fseTcJMiBo 'anticipate the 9 to 10 a.m. candle to "
                       "expand'; X4XSsv5CNqg 'the main TP final TP would be 10:00 a.m.'",
           "target": "corpus: 'No target is given for the anticipated 09:30 expansion in "
                     "this clip, only the entry and the stop'",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9, all events at 09:00 NY; "
                               "hold the clock fixed so the test reads the C2 direction"}
    return res, op, src, probe


def day_extremes(m1):
    mkt = cl.get_market(m1)
    td = trading_day(m1.index)
    codes, first = np.unique(td.to_numpy(), return_index=True)
    ends = np.r_[first[1:], len(td)]
    n = ends - first
    keep = n >= MIN_DAY_BARS
    first, ends, codes = first[keep], ends[keep], codes[keep]
    hi_p = np.array([s + int(np.argmax(mkt.h[s:e])) for s, e in zip(first, ends)])
    lo_p = np.array([s + int(np.argmin(mkt.l[s:e])) for s, e in zip(first, ends)])
    return mkt, first, ends, codes, hi_p, lo_p


def reading_b():
    m1 = cl.load_m1()
    mkt, first, ends, codes, hi_p, lo_p = day_extremes(m1)
    nm = mkt.nymod
    tn = mkt.tn
    # the window's first bar in each day, [09:30, 10:00)
    win_obs = np.full(len(first), np.nan)
    t930 = np.full(len(first), np.datetime64("NaT", "ns"))
    for j, (s, e) in enumerate(zip(first, ends)):
        w = np.flatnonzero((nm[s:e] >= WIN[0]) & (nm[s:e] < WIN[1]))
        if len(w) < 25:
            continue
        t930[j] = tn[s + w[0]]
        in_hi = WIN[0] <= nm[hi_p[j]] < WIN[1]
        in_lo = WIN[0] <= nm[lo_p[j]] < WIN[1]
        win_obs[j] = float(in_hi or in_lo)
    ok = np.isfinite(win_obs)
    first, ends, hi_p, lo_p, win_obs, t930 = (first[ok], ends[ok], hi_p[ok], lo_p[ok],
                                              win_obs[ok], t930[ok])
    t = pd.DatetimeIndex(t930).tz_localize("UTC")
    span = np.timedelta64(30, "m").astype("timedelta64[ns]")
    one = np.timedelta64(1, "m").astype("timedelta64[ns]")
    last_start = np.searchsorted(tn, tn[ends - 1] + one - span, side="right")
    cnt = np.maximum(last_start - first, 1)
    th, tl = tn[hi_p], tn[lo_p]

    def null_fn(rng, k):
        p = first + rng.integers(0, cnt)
        s0 = tn[p]
        s1 = s0 + span
        return (((th >= s0) & (th < s1)) | ((tl >= s0) & (tl < s1))).astype(float)

    res = cl.rate_test(win_obs, t, available_at=t, null_fn=null_fn, claim="+")
    op = {"rules": [
        "trading days (18:00 NY roll) with >= 1,200 M1 bars and >= 25 bars in 09:30-10:00",
        "hit = the day's high or low (first M1 bar printing it) starts in [09:30, 10:00) NY",
        "null = a random 30-minute window starting at a random M1 bar of the same trading "
        "day (ending by its last bar) contains the day's high or low"],
        "params": {"window": "09:30-10:00", "min_day_bars": MIN_DAY_BARS,
                   "day_open_hour": 18}}
    src = {"window": "corpus: X4XSsv5CNqg 'the volatility from 9:30 to 10:00'; "
                     "W7Fu3Rx5iMs 'ideally this hits before 10:00 a.m.'",
           "min_day_bars": "declared-before-run: skip stub sessions (README trap 6)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    return res, op, src


def show(res):
    print({k: res.get(k) for k in ("n", "observed_rate", "null_rate", "lift", "avg_R",
                                   "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "verdict", "verdict_detail", "ties", "ctrl_overlap",
                                   "halves", "exposure_bars", "sanity_flags")})


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        res, op, src, probe = reading_a()
        show(res)
        print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                              script=__file__, probe=probe,
                              notes="Reading a: the 8 a.m. hourly C2 reversal traded into "
                                    "the 9-10 candle. The corpus preconditions name index "
                                    "futures; gold is tested as the only instrument."))
    if "b" in which:
        res, op, src = reading_b()
        show(res)
        print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                              script=__file__,
                              no_detector="pure clock rule: the 09:30-10:00 NY window is a "
                                          "fixed wall-clock window; the outcome is the "
                                          "day's extreme timestamp",
                              notes="Reading b: does the 09:30-10:00 window hold the day's "
                                    "high/low more often than a random 30-minute window of "
                                    "the same day? A clock-share null; it measures "
                                    "opportunity (where extremes form), not tradeable "
                                    "accuracy (vault: Session Timing on Gold)."))
