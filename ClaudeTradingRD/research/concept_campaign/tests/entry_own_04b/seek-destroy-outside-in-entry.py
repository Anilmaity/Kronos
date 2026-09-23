"""seek-destroy-outside-in-entry — rate_test.

Concept (4WCiIyCiBrQ, "ICT Daily Profile - Seek & Destroy"): instead of trading breakouts,
wait for price to deviate OUTSIDE the reference range and fail to displace, then trade back
INTO it; first target = the range's equilibrium. Any interior reference (Asia range) is a
magnet price returns to after each excursion. No stop is ever given, so the claim is tested
as a level prediction (the concept's own measurable: "how often price returns to range
equilibrium after an unheld excursion outside the Asia/London range").

Event: the first 15m bar after 00:00 NY (before 12:00 NY) that trades beyond an Asia-range
(20:00-00:00 NY) extreme and CLOSES back inside, with no earlier post-midnight 15m close
beyond that extreme (a close beyond = displacement, threshold_fits grade A). One per day.
Outcome: the Asia EQ (0.5) is touched from the next M1 open until 12:00 NY.
Null: same signed distance from the M1 open at matched random moments (+/-30 d, NY time of
day +/-30 min), same number of M1 bars. claim '+'.

All parameters are declared here before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TF = "15min"
ASIA = (20 * 60, 24 * 60)     # 20:00-00:00 NY
TRADE_WIN = (0, 12 * 60)      # 00:00-12:00 NY
MIN_ASIA_BARS = 12            # of 16 15m bars
HORIZON_END_NY = 12           # outcome window ends 12:00 NY
NULL_TOD_TOL = 30


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    cols = ["decision_time", "available_at", "direction", "eq", "asia_hi", "asia_lo"]
    if b.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(b.index)
    mod = cl.ny_minute_of_day(t)
    td = np.asarray(cl.trading_day(t))
    b = b.assign(mod=mod, td=td)
    asia = b[(b["mod"] >= ASIA[0]) & (b["mod"] < ASIA[1])]
    ag = asia.groupby("td").agg(hi=("high", "max"), lo=("low", "min"), n=("high", "size"),
                                last_close=("close_time", "max"))
    ag = ag[ag["n"] >= MIN_ASIA_BARS]
    day = b[(b["mod"] >= TRADE_WIN[0]) & (b["mod"] < TRADE_WIN[1])]
    rows = []
    for d_, g in day.groupby("td", sort=True):
        if d_ not in ag.index:
            continue
        hi, lo = ag.at[d_, "hi"], ag.at[d_, "lo"]
        closed_above = closed_below = False
        for r in g.itertuples():
            if r.close_time <= ag.at[d_, "last_close"]:
                continue
            up = (r.high > hi) and not closed_above and (r.close <= hi) and (r.close >= lo)
            dn = (r.low < lo) and not closed_below and (r.close >= lo) and (r.close <= hi)
            if up and dn:                      # swept both sides in one bar: ambiguous
                break
            if up or dn:
                rows.append({"decision_time": r.close_time, "available_at": r.close_time,
                             "direction": -1 if up else 1, "eq": (hi + lo) / 2.0,
                             "asia_hi": hi, "asia_lo": lo})
                break
            closed_above |= r.close > hi
            closed_below |= r.close < lo
            if closed_above and closed_below:
                break
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"]).as_unit("ns")
    out["available_at"] = out["decision_time"]
    return out[cols].reset_index(drop=True)


def horizon_end(times: pd.DatetimeIndex) -> pd.DatetimeIndex:
    ny = times.tz_convert("America/New_York")
    end = (ny.normalize() + pd.Timedelta(hours=HORIZON_END_NY)).tz_localize(None)
    return end.tz_localize("America/New_York", ambiguous="NaT",
                           nonexistent="shift_forward").tz_convert("UTC")


if __name__ == "__main__":
    ev = cl.cache_frame(f"sd_outin_{TF}_asia{MIN_ASIA_BARS}", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print(len(ev), "probe", probe.get("passed"), ev["direction"].value_counts().to_dict())
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    i0 = mkt.pos_at_or_after(t)
    nb = mkt.pos_at_or_after(horizon_end(t)) - i0
    keep = nb > 0
    nb = np.maximum(nb, 1)
    px0 = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    eq = ev["eq"].to_numpy(float)
    dist = eq - px0                          # signed distance to the target
    side = np.where(dist >= 0, "above", "below")

    def hit(times, level, bars_, sides):
        out = np.full(len(times), np.nan)
        for s in ("below", "above"):
            m = sides == s
            if m.any():
                out[m] = cl.touch(pd.DatetimeIndex(times[m]), level[m], s,
                                  horizon_bars=bars_[m])["hit"].to_numpy()
        return out

    obs = hit(t, eq, nb, side)
    obs[~keep] = np.nan
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=NULL_TOD_TOL)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        pk = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        out[ok] = hit(tk[ok], pk + dist[ok], nb[ok], side[ok])
        out[~keep] = np.nan
        return out

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, predictors=ev)
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "reference range = Asia range, 15m bars 20:00-00:00 NY of the trading day "
        "(>= 12 of 16 bars present); EQ = its midpoint",
        "event: first 15m bar closing between 00:00 and 12:00 NY that trades beyond an Asia "
        "extreme and closes back inside, with no earlier post-Asia 15m close beyond that "
        "extreme (failure to displace); a bar sweeping both sides ends the day; one per day",
        "outcome: Asia EQ touched from the next M1 open until 12:00 NY",
        "null: same signed distance from the M1 open at matched random moments (+/-30d, NY "
        "time of day +/-30 min), same number of M1 bars"],
        "params": {"tf": TF, "asia": "20:00-00:00", "trade_win": "00:00-12:00",
                   "min_asia_bars": MIN_ASIA_BARS, "horizon_end": "12:00",
                   "null_tod_tol_min": NULL_TOD_TOL}}
    src = {"tf": "corpus: concept timeframes ltf 15m",
           "asia": "session_window_fit: forex Asia killzone 20:00-00:00 NY (verbatim)",
           "trade_win": "declared-before-run: London + NY AM, from midnight to 12:00 NY",
           "min_asia_bars": "declared-before-run: skip stub Asia sessions (trap 6)",
           "horizon_end": "session_window_fit: ny_am window ends 12:00 NY",
           "null_tod_tol_min": "declared-before-run: hold NY clock fixed in the null (trap 9)"}
    p = cl.write_result("seek-destroy-outside-in-entry", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="The Seek & Destroy day classification is a hindsight/"
                              "discretionary profile read and is not applied: the outside-in "
                              "EQ-magnet claim is tested on every day with an unheld Asia "
                              "excursion. No stop is stated, hence a rate test not a trade test. "
                              f"{int((~keep).sum())} events with no bar before 12:00 NY scored NaN.")
    print(p)
