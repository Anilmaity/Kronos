"""previous-day-lookback-three-days (liquidity, TTrades own voice, specified) — batch liquidity_own_01b.

FXJBFbZQbck: "for me that is three days that I will look back into price action" — mark the
high and low of each of the last three days, extend them forward, use them as targets.

The 1-day-old level is previous-period-high-low's job; what this concept adds is that the
2- and 3-day-old extremes are still live draws. Rate test: at each trading-day close
(the close of D-1), every high/low of D-2 and D-3 that has NOT been traded through since
it formed (through D-1's close) and is still beyond day D's first open is a row; hit = day
D trades to it. Null: the same signed distance from day D's first open, on a random other
session open within +/-30 days (same NY clock), same bar count.
All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from concept_lab.data import utc_ns

MIN_DAY_BARS = 600
TOD_TOL = 30
LOOKBACK_DAYS = 3


def daily(m1):
    d = cl.build_bars(m1, "1D")
    return d[d["n_m1"] > MIN_DAY_BARS]


def detect(m1):
    d = daily(m1)
    h, l = d["high"].to_numpy(), d["low"].to_numpy()
    t = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC")
    rows = []
    n = len(d)
    for age in (2, 3):                     # age relative to day D; the decision is D-1's close
        k = age - 1                        # offset back from the decision day (D-1)
        for i in range(k, n):
            j = i - k                      # the level's own day
            hi_since = h[j + 1:i + 1].max()
            lo_since = l[j + 1:i + 1].min()
            if h[j] > hi_since:
                rows.append((t[i], h[j], 1, age))
            if l[j] < lo_since:
                rows.append((t[i], l[j], -1, age))
    out = pd.DataFrame(rows, columns=["decision_time", "level", "side", "age"])
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"]).tz_convert("UTC")
    out["available_at"] = out["decision_time"]
    out = out[["decision_time", "available_at", "level", "side", "age"]]
    return out.sort_values(["decision_time", "age", "side"]).reset_index(drop=True)


def outcome_and_null(ev, full_daily):
    """hit during the next real session (its M1 bar count), and a matched null."""
    mkt = cl.get_market()
    ct = pd.DatetimeIndex(full_daily["close_time"]).tz_convert("UTC")
    nb = full_daily["n_m1"].to_numpy()
    t = pd.DatetimeIndex(ev["decision_time"])
    pos = np.searchsorted(utc_ns(ct), utc_ns(t))                 # row of this day in full_daily
    nxt = pos + 1
    has = nxt < len(full_daily)
    hb = np.where(has, nb[np.minimum(nxt, len(nb) - 1)], 0)
    i0 = mkt.pos_at_or_after(t)
    ok = has & (i0 < len(mkt.o))
    first_px = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    start = pd.DatetimeIndex(mkt.tn[np.minimum(i0, len(mkt.o) - 1)]).tz_localize("UTC")
    lvl = ev["level"].to_numpy()
    side = ev["side"].to_numpy()
    dist = lvl - first_px
    ok &= np.sign(dist) == side                     # level still untaken at the session open
    obs = np.full(len(ev), np.nan)
    for s, nm in ((1, "above"), (-1, "below")):
        r = ok & (side == s)
        if r.any():
            obs[r] = cl.touch(t[r], lvl[r], nm, horizon_bars=hb[r])["hit"].to_numpy()
    # null: sample around the session's first bar so the NY clock is matched (18:00 open)
    rt = cl.sample_times(start, 5, 30, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(ev), np.nan)
        good = ok & ~tk.isna()
        for s, nm in ((1, "above"), (-1, "below")):
            r = good & (side == s)
            if r.any():
                px = mkt.o[mkt.pos_at_or_after(tk[r])]
                out[r] = cl.touch(tk[r], px + dist[r], nm, horizon_bars=hb[r])["hit"].to_numpy()
        return out
    return obs, null_fn


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"pdl3_min{MIN_DAY_BARS}", lambda: detect(m1))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    obs, null_fn = outcome_and_null(ev, daily(m1))
    res = cl.rate_test(obs, ev["decision_time"], available_at=ev["available_at"],
                       null_fn=null_fn, predictors=ev, claim="+")
    print({k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail")})
    for a in (2, 3):
        s = (ev["age"].to_numpy() == a) & np.isfinite(obs)
        print("age", a, int(s.sum()), float(np.nanmean(obs[s])))
    op = {"rules": ["at each trading-day close (D-1), take the highs and lows of D-2 and D-3",
                    "keep a level only if no later day through D-1 traded beyond it (still untaken) and it is still beyond day D's first open",
                    "hit = day D trades to it (any M1 high >= level above / low <= level below)",
                    "claim: 2-3-day-old untaken daily extremes are reached more often than an arbitrary level at the same distance"],
          "params": {"lookback_days": LOOKBACK_DAYS, "ages_tested": [2, 3], "day_unit": "trading days (NY 18:00 roll), stub sessions dropped",
                     "min_day_bars": MIN_DAY_BARS, "horizon": "next session (M1 bars)",
                     "null": "distance-matched, clock-matched +/-30min, +/-30d, 5 reps"}}
    src = {"lookback_days": "corpus: FXJBFbZQbck 'for me that is three days that I will look back into price action'",
           "ages_tested": "declared-before-run: the 1-day-old level is previous-period-high-low's test; this concept's addition is the 2- and 3-day-old levels",
           "day_unit": "declared-before-run: trading days (ambiguity: trading vs calendar not stated); session_window_fit 18:00 NY roll",
           "min_day_bars": "declared-before-run: drop stub sessions <=600 M1 bars (README trap 6)",
           "horizon": "declared-before-run: the next real session, in M1 bars",
           "null": "declared-before-run: same signed distance from the next session's first open, random other session open +/-30d, NY clock +/-30min, same bar count, 5 reps"}
    notes = ("Target/draw reading of the three-day lookback. Untaken = not traded beyond by any later day up to the decision. "
             "The 'confluence for reactions' use (deviation-and-retest box setup) is not separately tested.")
    p = cl.write_result("previous-day-lookback-three-days", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print("wrote", p)
