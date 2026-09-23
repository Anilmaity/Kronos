"""session-open-volume-nyse (TTrades own voice, contested).  Claim: 09:30 NY is a time level
only for INDICES (the NYSE cash open brings volume); on forex-class instruments 09:30 has no
comparable effect, and 08:30 is the usable level 'when there is news at that time'.
Gold is forex-class here (method_spec §1.4: forex grid for gold; spot XAUUSD).
No volume in the data -> the effect is read as a realised-range step-up (the concept's own
measurable: 'realised range in the 15 minutes after ... versus before').  Pure clock rule,
no detector.  Two readings (rate_test):

(a) asset-class reading: on gold the 08:30 open is a time level and 09:30 is not.
    per NY weekday session with >= 10 M1 bars in each window:
      step(T) = range of M1 bars in [T, T+15m) > range in [T-15m, T)
    observed = step(08:30); null = step(09:30) on the SAME day (paired).  claim '+'.
(b) news reading: 08:30 is usable on forex when a release lands at 08:30.
    observed = step(08:30) on NFP days (the one high-impact 08:30 release whose schedule is
    mechanically derivable; no calendar dataset exists); null = step(08:30) on 5 random
    non-NFP weekdays within +/-30 days (seeded rng from rate_test).  claim '+'.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
from _common import cl, nfp_dates, show  # noqa: E402

WIN_MIN = 15
MIN_BARS = 10


def step_table(m1, hhmm):
    h, m = map(int, hhmm.split(":"))
    T = h * 60 + m
    loc = cl.to_ny(m1.index)
    mod = (loc.hour * 60 + loc.minute).to_numpy()
    date = loc.tz_localize(None).normalize()
    out = {}
    for name, lo, hi in (("before", T - WIN_MIN, T), ("after", T, T + WIN_MIN)):
        sel = (mod >= lo) & (mod < hi)
        g = pd.DataFrame({"d": date[sel], "h": m1["high"].to_numpy()[sel],
                          "l": m1["low"].to_numpy()[sel]}).groupby("d")
        out[name] = g.agg(h=("h", "max"), l=("l", "min"), n=("h", "size"))
    df = out["before"].join(out["after"], lsuffix="_b", rsuffix="_a", how="inner")
    df = df[(df["n_b"] >= MIN_BARS) & (df["n_a"] >= MIN_BARS)]
    df = df[df.index.dayofweek < 5]
    df["step"] = ((df["h_a"] - df["l_a"]) > (df["h_b"] - df["l_b"])).astype(float)
    df["T"] = (df.index + pd.Timedelta(minutes=T)).tz_localize(
        "America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    return df.dropna(subset=["T"])


if __name__ == "__main__":
    m1 = cl.load_m1()
    s830, s930 = step_table(m1, "08:30"), step_table(m1, "09:30")
    base_src = {"tz": "method_spec: §1.4 DST settled, America/New_York",
                "win_min": "declared-before-run: 15 minutes, the concept's measurable ('in the 15 minutes after 09:30 versus before')",
                "min_bars": "declared-before-run: >= 10 of 15 M1 bars in each window",
                "measure": "declared-before-run: range step-up indicator (no volume in the data)"}
    base_par = {"tz": "America/New_York", "win_min": WIN_MIN, "min_bars": MIN_BARS,
                "measure": "range[T,T+15) > range[T-15,T)"}

    # (a) paired 08:30 vs 09:30
    j = s830.join(s930[["step"]], rsuffix="_930", how="inner")
    t = pd.DatetimeIndex(j["T"])
    print("a", len(j), j["step"].mean(), j["step_930"].mean())
    res = cl.rate_test(j["step"].to_numpy(), t, available_at=t, null=j["step_930"].to_numpy())
    show(res)
    op = {"rules": ["per NY weekday with >= 10 M1 bars in each 15-minute window",
                    "step(T) = high-low of M1 bars in [T, T+15m) exceeds that of [T-15m, T)",
                    "observed = step(08:30 NY); null = step(09:30 NY) the same day (paired comparator); claim 08:30 is the forex-class time level, 09:30 is not"],
          "params": {**base_par, "observed_time": "08:30", "null_time": "09:30"}}
    src = {**base_src, "observed_time": "corpus: wGYde-h84cs / session-open-volume-nyse.yaml 'For forex: 08:30 is usable when a release lands at that time'",
           "null_time": "corpus: wGYde-h84cs 'that's when the stock New York Stock Exchange opens' ('For forex: do not use 09:30 as a structural time level')"}
    print(cl.write_result("session-open-volume-nyse", "a", res, operationalization=op, params_source=src,
                          script=__file__, no_detector="pure clock rule: 15-minute M1 ranges either side of fixed NY times; no detector",
                          notes="Reading a compares two time levels on the same days; the 'null' is the 09:30 comparator, not a random-time null."))

    # (b) 08:30 on NFP days vs 08:30 on random non-NFP weekdays within +/-30d
    nfp = set(pd.DatetimeIndex(nfp_dates()))
    is_nfp = np.array([d in nfp for d in s830.index])
    obs_df = s830[is_nfp]
    pool = s830[~is_nfp]
    pool_d = pool.index.to_numpy()
    pool_step = pool["step"].to_numpy()
    od = obs_df.index.to_numpy()
    lo = np.searchsorted(pool_d, od - np.timedelta64(30, "D"), "left")
    hi = np.searchsorted(pool_d, od + np.timedelta64(30, "D"), "right")
    t = pd.DatetimeIndex(obs_df["T"])
    print("b", len(obs_df), obs_df["step"].mean(), pool["step"].mean())

    def null_fn(rng, k):
        u = rng.integers(lo, np.maximum(hi, lo + 1))
        out = np.where(hi > lo, pool_step[np.minimum(u, len(pool_step) - 1)], np.nan)
        return out

    res = cl.rate_test(obs_df["step"].to_numpy(), t, available_at=t, null_fn=null_fn)
    show(res)
    op = {"rules": ["as (a); observed = step(08:30 NY) on NFP days",
                    "NFP days: BLS reference-week rule (third Friday after the Saturday ending the week containing the 12th of the prior month; Jul 3/4 and Jan 1 adjustments; 2025 shutdown releases special-cased)",
                    "null = step(08:30 NY) on a random non-NFP weekday within +/-30 days, 5 draws"],
          "params": {**base_par, "observed_time": "08:30", "news": "NFP only", "null_window_days": 30}}
    src = {**base_src, "observed_time": "corpus: session-open-volume-nyse.yaml 'For forex: 08:30 is usable when a release lands at that time'",
           "news": "declared-before-run: NFP is the only 08:30 high-impact release whose dates are mechanically derivable; no calendar dataset in the workspace",
           "null_window_days": "declared-before-run: the locked +/-30-day regime window"}
    print(cl.write_result("session-open-volume-nyse", "b", res, operationalization=op, params_source=src,
                          script=__file__, no_detector="pure clock/calendar rule: 15-minute M1 ranges either side of 08:30 NY on rule-derived NFP dates; no detector",
                          notes="Only ~125 NFP days exist in the certified span, so the effective n is below the 200 floor by construction; CPI/other 08:30 releases stay in the null pool (attenuates toward 0)."))
