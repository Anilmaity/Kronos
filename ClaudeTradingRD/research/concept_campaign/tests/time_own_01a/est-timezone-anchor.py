"""est-timezone-anchor (TTrades own voice, contested) — rate_test, two readings.

The concept: every clock time he uses is on the Eastern clock ("all times are shown in
Eastern Standard time"; "I'm always in New York local time"), and the levels on that clock
are where things happen. Contested point, stated in the concept's own ambiguities: literal
EST (fixed UTC-5 all year) versus the New York local clock (EST/EDT, DST-aware).

Decidable consequence, tested for each reading (declared before any run): a time level
marked on the stated clock is a real market event on gold. The level used is 08:30, the
level the concept keeps for forex-class instruments ("we don't really have the 930 open
with Forex"; 08:30 = "news embargo lifts"). Per weekday:
  T = 08:30 on the reading's clock
      a: America/New_York (DST-aware)       b: fixed UTC-5 (13:30 UTC all year)
  outcome = 1 if the summed M1 high-low over [T, T+15m) exceeds that over [T-15m, T)
            (both 15-minute blocks fully traded, else the day is dropped).
  null = the same comparison at matched random moments (sample_times, +/-30 days, 5 reps,
         same minute-of-hour grid), same completeness rule.
Claim '+': the stated clock's 08:30 marks a volatility step more often than a random
half-hour mark. The readings differ only on DST days (about 8 months a year), where
reading b's 08:30 falls at 09:30 New York.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from concept_lab.data import utc_ns  # noqa: E402

CID = "est-timezone-anchor"
P = {"level": "08:30", "block_min": 15, "weekdays_only": True}
READINGS = {"a": "America/New_York", "b": "Etc/GMT+5"}   # Etc/GMT+5 == fixed UTC-5


def main():
    m1 = cl.load_m1()
    mkt = cl.get_market(m1)
    tn = mkt.tn
    rng_ = mkt.h - mkt.l
    cs = np.concatenate([[0.0], np.cumsum(rng_)])
    k = P["block_min"]
    one = np.int64(60_000_000_000)

    def score(times):
        tt = pd.DatetimeIndex(times)
        ok0 = ~tt.isna()
        out = np.full(len(tt), np.nan)
        if ok0.sum() == 0:
            return out
        q = utc_ns(tt[ok0])
        p = np.searchsorted(tn, q, side="left")
        good = (p - k >= 0) & (p + k - 1 < len(tn))
        pc = np.clip(p, k, len(tn) - k)
        good &= (tn[np.minimum(p, len(tn) - 1)] == q)
        good &= (tn[pc + k - 1] == q + (k - 1) * one) & (tn[pc - k] == q - k * one)
        after = cs[pc + k] - cs[pc]
        before = cs[pc] - cs[pc - k]
        v = np.where(good, (after > before).astype(float), np.nan)
        out[np.flatnonzero(ok0)] = v
        return out

    start = m1.index.min().tz_convert("UTC").normalize()
    end = m1.index.max().tz_convert("UTC").normalize()
    dates = pd.date_range(start.tz_localize(None), end.tz_localize(None), freq="D")
    dates = dates[dates.dayofweek < 5]
    for rd, tz in READINGS.items():
        loc = pd.DatetimeIndex(dates + pd.Timedelta(hours=8, minutes=30)).tz_localize(tz)
        T = loc.tz_convert("UTC").as_unit("ns")
        obs = score(T)
        keep = np.isfinite(obs)
        T, obs = T[keep], obs[keep]
        rt = cl.sample_times(T, 5, 30, seed=cl.rules.SEED)

        def null_fn(rng, kk):
            return score(pd.DatetimeIndex(rt[:, kk]).tz_localize("UTC"))

        res = cl.rate_test(obs, T, available_at=T, null_fn=null_fn, claim="+")
        op = {"rules": [
            f"T = 08:30 on the {tz} clock, every weekday with data",
            "outcome = summed M1 high-low over [T, T+15m) > over [T-15m, T); both blocks "
            "fully traded (15 consecutive M1 bars each) else dropped",
            "null = same comparison at sample_times matched moments (+/-30d, 5 reps, same "
            "minute-of-hour grid), same completeness rule"],
            "params": dict(P, clock=tz)}
        src = {"level": "corpus: EYzP7c24AwM '8:30 is when the news embargo lifts or there's "
                        "high impact news' / 'we don't really have the 930 open with Forex'",
               "block_min": "declared-before-run: 15-minute blocks either side of the level",
               "weekdays_only": "declared-before-run: Mon-Fri calendar dates (no Saturday "
                                "session; Sunday 08:30 is closed)",
               "clock": ("corpus: JPVhmPZiLKY 'I'm always in New York local time'" if rd == "a"
                         else "corpus: EYzP7c24AwM 'all times are shown in Eastern Standard "
                              "time' read literally as fixed UTC-5")}
        notes = ("The concept is a clock convention; its decidable consequence tested here is "
                 "that 08:30 on the stated clock is a real volatility event on gold. The DST "
                 "question was already settled empirically (session_window_fit: the venue "
                 "break resumes at 18:00 NY on 99.8% of 605 occasions DST-aware). Compare "
                 "readings a vs b: they coincide in winter.")
        p = cl.write_result(CID, rd, res, operationalization=op, params_source=src,
                            script=__file__, notes=notes,
                            no_detector="pure clock rule: a fixed wall-clock time on a stated "
                                        "timezone; no detector")
        print(rd, p)
        for kk in ("n", "observed_rate", "null_rate", "lift", "verdict", "verdict_detail",
                   "diff", "ci_lo", "ci_hi", "p", "mde", "mde_threshold"):
            print("  ", kk, res.get(kk))


if __name__ == "__main__":
    main()
