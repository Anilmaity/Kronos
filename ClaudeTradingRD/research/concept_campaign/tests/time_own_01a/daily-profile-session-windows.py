"""daily-profile-session-windows (TTrades own voice, underspecified) — rate_test.

The concept: the daily-profile series is built on two clock windows, London 02:00-05:00
and New York a.m. 08:30-12:00; every profile is classified by what price did inside them.
Its own measurable: "how often the daily extreme forms inside 02:00-05:00 vs 08:30-12:00".
The predictive content is that the day's high and low are made inside these windows
(that is what makes them the windows a profile is read in).

Operationalisation (declared before any run):
  * trading day = 18:00 NY roll (the corpus daily candle); stub days with < 600 M1 bars
    are skipped (README trap 6; the harness's worked example uses the same floor);
  * per day, outcome = share of the day's two extremes (first M1 bar printing the day high,
    first printing the day low) whose bar starts inside [02:00,05:00) or [08:30,12:00) NY
    — 0, 0.5 or 1;
  * null (geometry-matched): the SAME two windows with the same lengths and the same gap
    between them, shifted as a block by a uniform random offset so that the block
    02:00-12:00 still lies inside the 23-hour trading day (18:00-17:00), scored on the
    same day's extremes; 5 reps (locked). This asks whether the stated placement beats the
    same amount of clock placed anywhere else in the day, which absorbs the arcsine
    (boundary) pile-up and the 18:00 reopen artefact on the null side too.
  * prediction time = the day's first M1 bar (the windows are fixed before the day opens).
Claim '+'.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

CID = "daily-profile-session-windows"
P = {"windows": [("02:00", "05:00"), ("08:30", "12:00")], "day_open_hour": 18,
     "min_day_m1": 600, "null": "block shift of both windows, uniform within the day",
     "tz": "America/New_York"}


def hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


if __name__ == "__main__":
    m1 = cl.load_m1()
    idx = m1.index
    td = cl.trading_day(idx, P["day_open_hour"])
    mod = cl.ny_minute_of_day(idx)
    roll = P["day_open_hour"] * 60
    msr = (mod - roll) % 1440                       # minutes since the 18:00 roll
    df = pd.DataFrame({"td": td.to_numpy(), "hi": m1["high"].to_numpy(),
                       "lo": m1["low"].to_numpy(), "msr": msr, "t": idx})
    g = df.groupby("td", sort=True)
    n_m1 = g.size()
    ihi = g["hi"].idxmax()                          # first occurrence of the max
    ilo = g["lo"].idxmin()
    keep = n_m1[n_m1 >= P["min_day_m1"]].index
    ihi, ilo = ihi.loc[keep].to_numpy(), ilo.loc[keep].to_numpy()
    msr_hi = df["msr"].to_numpy()[ihi]
    msr_lo = df["msr"].to_numpy()[ilo]
    first_t = pd.DatetimeIndex(g["t"].min().loc[keep])

    wins = [((hm(a) - roll) % 1440, (hm(z) - roll) % 1440) for a, z in P["windows"]]
    span_lo = min(a for a, _ in wins)                # 480  (02:00)
    span_hi = max(z for _, z in wins)                # 1080 (12:00)
    day_len = 23 * 60                                # 18:00 -> 17:00

    def inside(x, shift):
        r = np.zeros(len(x), bool)
        for a, z in wins:
            r |= (x >= a + shift) & (x < z + shift)
        return r

    obs = (inside(msr_hi, 0).astype(float) + inside(msr_lo, 0).astype(float)) / 2

    def null_fn(rng, k):
        s = rng.integers(-span_lo, day_len - span_hi + 1, size=len(obs))
        return (inside(msr_hi, s).astype(float) + inside(msr_lo, s).astype(float)) / 2

    res = cl.rate_test(obs, first_t, available_at=first_t, null_fn=null_fn, claim="+")
    op = {"rules": [
        "trading day = 18:00 NY roll; days with < 600 M1 bars skipped",
        "outcome per day = share of the day's high and low (first printing M1 bar) inside "
        "London 02:00-05:00 or New York a.m. 08:30-12:00 NY (DST-aware)",
        "null = the same two windows shifted together by a uniform random offset within the "
        "23h trading day (same lengths, same gap), scored on the same extremes; 5 reps",
        "prediction stamped at the day's first M1 bar"],
        "params": P}
    src = {"windows": "corpus: y6SnEdASVLY / xdzyejskSKE / IeXtmeKqjnQ / 4WCiIyCiBrQ (daily "
                      "profile series: London 02:00-05:00, NY a.m. 08:30-12:00); method_spec "
                      "session windows",
           "day_open_hour": "session_window_fit: 18:00 NY daily roll (corpus daily candle)",
           "min_day_m1": "declared-before-run: stub-session floor as in the harness worked "
                         "example (README trap 6)",
           "null": "declared-before-run: geometry-matched block shift of the same windows",
           "tz": "session_window_fit: America/New_York with DST (settled)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__,
                        no_detector="pure clock rule: fixed NY windows vs the day's M1 "
                                    "high/low; windows known before the day opens")
    print(p)
    for k in ("n", "observed_rate", "null_rate", "lift", "verdict", "verdict_detail",
              "diff", "ci_lo", "ci_hi", "p", "mde", "mde_threshold", "halves"):
        print("  ", k, res.get(k))
