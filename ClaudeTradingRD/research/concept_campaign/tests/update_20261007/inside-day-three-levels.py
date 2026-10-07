"""inside-day-three-levels — update u1007 (TTrades MNQ Cup afternoon, h1ZQWWQDhKA):
"We are double inside day ... We have not taken out either side of the range. So this is just
by definition consolidation. So, normally we're just going to be right around the EQ and the
opening price."  rate_test of the NEW element: the opening-price magnet on a (double) inside day.
(The PD-EQ reaction on inside days was the prior reading, liquidity_own_02b.)

Fixed BEFORE the first run.
Trading day rolls 18:00 NY; daily opening price = open of the day's first M1 bar.
Previous day (PD) = last completed trading day with >= 600 M1 bars (stub sessions skipped).
Decision: 12:00 NY (afternoon session, as in the stream), at the first M1 bar starting at/after
12:00 NY of the trading day; only bars before it are read.
Inside so far: running day high < PDH and running low > PDL up to the decision.
  reading u1007a ("double inside day" = two consecutive inside days): PD was itself inside its
                 own previous day (PDH < PPDH and PDL > PPDL) AND today is inside so far.
  reading u1007b ("double inside" = neither side of PD taken): today inside so far only.
Outcome: price trades back to the daily opening price (touch toward it from the decision-bar
open) between the decision and the end of the trading day (M1-bar horizon).
Null (AUDIT 2026-10-07, vault-aware re-run): the MIRROR level - same moment, same distance, same
M1-bar horizon, opposite side of the decision price. The first run drew the null at random
moments (+/-30d, +/-30 min NY clock), which matches the clock but not local volatility (vault:
Concept Campaign 2026-09-23 lesson 3). "Inside so far" selects narrow-range days: measured
median afternoon range event/null = 0.78 (u1007a) / 0.92 (u1007b), so that null was pushed
toward NEGATIVE by quietness, which the concept itself asserts ("by definition consolidation").
The mirror holds volatility, clock, day and horizon fixed and asks only the claim: does price
return to the opening price more often than it travels the same distance away from it?
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "inside-day-three-levels"
MIN_BARS = 600
DEC_MIN = 12 * 60  # 12:00 NY


def detect(m1, consecutive):
    td = cl.trading_day(m1.index).to_numpy()
    days, start = np.unique(td, return_index=True)
    order = np.argsort(start); days, start = days[order], start[order]
    end = np.r_[start[1:], len(m1)]
    H, L, O = (m1[c].to_numpy(float) for c in ("high", "low", "open"))
    nym = cl.ny_minute_of_day(m1.index)
    dh = np.maximum.reduceat(H, start); dl = np.minimum.reduceat(L, start)
    nb = end - start
    out = []
    prev = pprev = -1
    for k in range(len(days)):
        s, e = start[k], end[k]
        if prev >= 0 and (not consecutive or pprev >= 0):
            pdh, pdl = dh[prev], dl[prev]
            pd_inside = pprev >= 0 and pdh < dh[pprev] and pdl > dl[pprev]
            # the 11:59 NY M1 bar; decision at its close (12:00 NY) - days missing it are skipped
            cand = np.flatnonzero(nym[s:e] == DEC_MIN - 1)
            if len(cand) and (pd_inside or not consecutive):
                i = s + cand[0] + 1   # bars s..i-1 are read; decision = close of bar i-1
                if H[s:i].max() < pdh and L[s:i].min() > pdl:
                    out.append((i, O[s], pdh, pdl))
        if nb[k] >= MIN_BARS:
            pprev, prev = prev, k
    cols = ["decision_time", "available_at", "day_open", "pdh", "pdl"]
    if not out:
        return pd.DataFrame(columns=cols)
    r = np.array(out, dtype=float)
    t = pd.DatetimeIndex(m1.index[r[:, 0].astype(int) - 1]).tz_convert("UTC") + pd.Timedelta(minutes=1)
    return pd.DataFrame({"decision_time": t, "available_at": t, "day_open": r[:, 1],
                         "pdh": r[:, 2], "pdl": r[:, 3]})


def run(reading, consecutive):
    det = lambda m1: detect(m1, consecutive)
    ev = cl.cache_frame(f"{CID}_u1007_{reading}", lambda: detect(cl.load_m1(), consecutive))
    print(reading, len(ev))
    probe = cl.probe_lookahead(det, ev, lookback="10D")
    m1 = cl.load_m1(); mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    td_all = cl.trading_day(m1.index).to_numpy()
    last_of_day = pd.Series(np.arange(len(m1))).groupby(td_all).max()
    i0 = mkt.pos_at_or_after(t)
    hb = np.maximum((last_of_day.reindex(cl.trading_day(t).to_numpy()).to_numpy() - i0 + 1), 1).astype(np.int64)
    p0 = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    dist = ev["day_open"].to_numpy() - p0                     # signed distance to the open
    side = np.where(dist >= 0, "above", "below")

    mside = np.where(dist >= 0, "below", "above")              # mirror: away from the open

    def hit(lvl, sides):
        o = np.zeros(len(t))
        for sd in ("above", "below"):
            m = sides == sd
            if m.any():
                o[m] = cl.touch(t[m], lvl[m], sd, horizon_bars=hb[m])["hit"].to_numpy()
        return o

    obs = hit(ev["day_open"].to_numpy(), side)
    mirror = hit(p0 - dist, mside)     # same moment, distance, horizon; opposite side (vol-matched)
    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]), null=mirror,
                       predictors=ev)
    rules = ["trading day rolls 18:00 NY; daily opening price = open of the day's first M1 bar",
             "PD = last completed trading day with >= 600 M1 bars",
             "decision at the close of the 11:59 NY M1 bar (12:00 NY); days missing that bar skipped",
             "inside so far: running day high < PDH and running low > PDL at the decision",
             ("double inside = PD inside its own previous day AND today inside so far" if consecutive
              else "double inside = today has taken neither PDH nor PDL (inside so far)"),
             "hit: price touches the daily opening price (from the decision-bar open toward it) by end of trading day, M1-bar horizon",
             "null: mirror level - same decision moment, same distance, same M1-bar horizon, opposite side of the decision price (holds local volatility, clock and day fixed)"]
    params = {"day_open_hour": 18, "min_prev_day_bars": MIN_BARS, "decision_ny": "12:00",
              "double_inside": "consecutive inside days" if consecutive else "neither PD side taken",
              "level": "daily opening price (18:00 NY open)", "horizon": "rest of trading day, M1 bars",
              "null": "mirror level, same moment/distance/horizon"}
    src = {"day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "min_prev_day_bars": "declared-before-run: skip stub sessions (trap 6), as prior reading",
           "decision_ny": "corpus: h1ZQWWQDhKA title 'TTrades MNQ Cup - Afternoon Session'; declared-before-run 12:00 NY as afternoon start",
           "double_inside": ("corpus: h1ZQWWQDhKA 'We are double inside day' - reading a: two consecutive inside days (draft detection rule)"
                             if consecutive else
                             "corpus: h1ZQWWQDhKA 'We have not taken out either side of the range' - reading b: neither PD side taken"),
           "level": "corpus: h1ZQWWQDhKA 'normally we're just going to be right around the EQ and the opening price'; opening price = the new element (EQ tested in prior reading)",
           "horizon": "declared-before-run: claim is about the current day",
           "null": ("declared-before-run: audit 2026-10-07 (pre-fix diagnostic disclosed in notes); vault Concept Campaign 2026-09-23 lesson 3 'rate nulls must match time of day and local "
                    "volatility'; the first run's random-moment null matched the clock only, and inside-so-far days are a "
                    "low-volatility selection (afternoon range event/null 0.78 a, 0.92 b); mirror has no free parameter")}
    notes = ("Tests the opening-price magnet only; the PD-EQ part of the claim overlaps the prior reading. "
             "Inside-day read causally (inside so far at 12:00 NY). MNQ source applied to XAUUSD. "
             "AUDIT re-run: null changed from random moments (clock-matched only) to the same-moment mirror level. "
             "Disclosure: the mirror touch rates were computed in a pre-fix diagnostic (open 0.297 vs mirror 0.432 a; "
             "0.318 vs 0.365 b) alongside the volatility check that motivated the change. Mirror caveat: a "
             "continuation (intraday momentum) day favours the mirror, which is the alternative the claim denies.")
    p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print({k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail")})
    print(p)


if __name__ == "__main__":
    run("u1007a", True)
    run("u1007b", False)
