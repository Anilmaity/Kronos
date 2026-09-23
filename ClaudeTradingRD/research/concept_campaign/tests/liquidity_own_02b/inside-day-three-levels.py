"""inside-day-three-levels — on an inside day only PDH, PD-EQ and PDL matter; work from the
EQ first: a reaction at the EQ projects to the previous day's extreme on the bias side, and
a trade through the EQ is a liquidity sweep, not an invalidation. rate_test.

Fixed BEFORE the first run.
Trading day rolls 18:00 NY. Previous day = the last completed trading day with >= 600 M1 bars
(stub sessions skipped). 'Inside day' can only be known causally as INSIDE SO FAR: the day's
running high < PDH and running low > PDL through the moment in question.
Event: the FIRST M1 bar of the day that trades through PD-EQ = (PDH+PDL)/2, provided the day
is still inside so far at that bar's close. Bias side = the side of the EQ the day OPENED on
(opened above -> price came down to the EQ -> bullish case, expect PDH; mirrored) — the
concept gives the bullish case only and names no bias rule, so this is the declared proxy.
Decision = close of the touch bar.
Outcome: the bias-side extreme (PDH for bullish) is traded BEFORE the opposite one (PDL),
from the next M1 bar to the end of that trading day (M1-bar horizon); neither -> 0; both in the
same M1 bar -> 0.5.
Null (geometry-matched): at 5 matched random moments (+/-30 days), the same up/down distances
from that moment's price, the same horizon in M1 bars, the same side asked.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "inside-day-three-levels"
MIN_BARS = 600


def detect(m1):
    td = cl.trading_day(m1.index)
    tdv = td.to_numpy()
    days, start = np.unique(tdv, return_index=True)
    order = np.argsort(start); days, start = days[order], start[order]
    end = np.r_[start[1:], len(m1)]
    H, L, O = m1["high"].to_numpy(float), m1["low"].to_numpy(float), m1["open"].to_numpy(float)
    dh = np.maximum.reduceat(H, start); dl = np.minimum.reduceat(L, start)
    nb = end - start
    out = []
    prev = -1
    for k in range(len(days)):
        if prev >= 0:
            pdh, pdl = dh[prev], dl[prev]
            eq = 0.5 * (pdh + pdl)
            s, e = start[k], end[k]
            op = O[s]
            if op != eq and pdl < op < pdh:
                hh = np.maximum.accumulate(H[s:e]); ll = np.minimum.accumulate(L[s:e])
                tch = np.flatnonzero((L[s:e] <= eq) & (H[s:e] >= eq))
                if len(tch):
                    i = tch[0]
                    if hh[i] < pdh and ll[i] > pdl:
                        out.append((s + i, 1 if op > eq else -1, pdh, pdl, eq))
        if nb[k] >= MIN_BARS:
            prev = k
    if not out:
        return pd.DataFrame(columns=["decision_time", "available_at", "side", "pdh", "pdl", "eq"])
    r = np.array(out, dtype=float)
    idx = r[:, 0].astype(int)
    t = pd.DatetimeIndex(m1.index[idx]).tz_convert("UTC") + pd.Timedelta(minutes=1)
    return pd.DataFrame({"decision_time": t, "available_at": t, "side": r[:, 1].astype(int),
                         "pdh": r[:, 2], "pdl": r[:, 3], "eq": r[:, 4]})


def first_side(times, up, dn, side, hbars):
    a = cl.touch(times, up, "above", horizon_bars=hbars)
    b = cl.touch(times, dn, "below", horizon_bars=hbars)
    ta = pd.DatetimeIndex(a["hit_time"]); tb = pd.DatetimeIndex(b["hit_time"])
    ha, hb = a["hit"].to_numpy(), b["hit"].to_numpy()
    tan = np.where(ha, cl.data.utc_ns(ta.fillna(pd.Timestamp("2100-01-01", tz="UTC"))), np.datetime64("2262-01-01"))
    tbn = np.where(hb, cl.data.utc_ns(tb.fillna(pd.Timestamp("2100-01-01", tz="UTC"))), np.datetime64("2262-01-01"))
    up_first = np.where(ha & (~hb | (tan < tbn)), 1.0, 0.0)
    dn_first = np.where(hb & (~ha | (tbn < tan)), 1.0, 0.0)
    tie = ha & hb & (tan == tbn)
    res = np.where(side > 0, up_first, dn_first)
    return np.where(tie, 0.5, res)


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["side"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    # horizon: M1 bars from the next bar to the end of the touch's trading day (outcome side only)
    td_all = cl.trading_day(m1.index).to_numpy()
    tdn = cl.data.utc_ns(pd.DatetimeIndex(m1.index))
    last_of_day = pd.Series(np.arange(len(m1))).groupby(td_all).max()
    i0 = mkt.pos_at_or_after(t)
    tday = cl.trading_day(t - pd.Timedelta(minutes=1)).to_numpy()
    hb = (last_of_day.reindex(tday).to_numpy() - i0 + 1).astype(np.int64)
    ok = hb > 0
    p0 = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    up_d = ev["pdh"].to_numpy() - p0
    dn_d = p0 - ev["pdl"].to_numpy()
    side = ev["side"].to_numpy()
    obs = first_side(t, ev["pdh"].to_numpy(), ev["pdl"].to_numpy(), side, np.maximum(hb, 1))
    obs = np.where(ok & (up_d > 0) & (dn_d > 0), obs, np.nan)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        good = ~tk.isna() & ok
        out = np.full(len(t), np.nan)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[good]), len(mkt.o) - 1)]
        out[good] = first_side(tk[good], px + up_d[good], px - dn_d[good], side[good],
                               np.maximum(hb[good], 1))
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]), null_fn=null_fn,
                       predictors=ev)
    rules = ["trading day rolls 18:00 NY; previous day = last completed day with >= 600 M1 bars",
             "inside so far: running day high < PDH and running low > PDL",
             "event: first M1 bar of the day trading through PD-EQ=(PDH+PDL)/2 while inside so far; day must open strictly inside the PD range",
             "bias side = side of the EQ the day opened on (above -> bullish -> PDH)",
             "hit: bias-side PD extreme traded before the opposite one, next M1 bar to end of that trading day (M1-bar horizon); same-bar both = 0.5",
             "null: same up/down distances and bar horizon from matched random moments (5 reps, +/-30d), same side"]
    params = {"day_open_hour": 18, "min_prev_day_bars": MIN_BARS, "eq": "full-range midpoint",
              "bias_proxy": "open side of EQ", "horizon": "rest of the trading day, in M1 bars"}
    src = {"day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "min_prev_day_bars": "declared-before-run: skip data-hole stub sessions (trap 6), as in the harness rate example",
           "eq": "method_spec: §2.4 'the EQ of the previous day's range' (full range; body-EQ ambiguity noted in the concept)",
           "bias_proxy": "declared-before-run: the concept names no bias rule for inside days; opening side of EQ = the side price travels from to reach the EQ",
           "horizon": "declared-before-run: the claim is about the current (inside) day"}
    notes = ("Inside-day is read causally (inside so far), since a completed inside day is only known at "
             "its close. The EQ-first reaction is the concept's first measurable ('reaction rate at previous "
             "day EQ on inside days'). The unpublished inside-day entry model is out of scope by design.")
    p = cl.write_result(CID, None, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print({k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail")})
    print(p)
