"""ten-am-candle-alignment — 10:00 a.m.: new 4H/1H/30m/15m candles open at once.

Contested concept; two readings (rate_test), declared before the first run.

Reading a (claim '-') — the deadline: "if the 9:30 move has not reached its objective by
10:00 the day is read as consolidation and the idea is dropped" (measurable: "hit rate of
the opening idea when the objective is unmet at 10:00").
  * objective as in nine-thirty-expansion-invalidation: at 09:30 NY, the previous
    trading day's high/low (18:00 roll, min_coverage 0.5) not yet traded through this
    trading day, the nearer to the 09:29 close if both remain.
  * predictor row at 10:00 NY when the 09:30-09:59 M1 bars did NOT reach it.
  * hit = price reaches the objective within the next 120 M1 bars (10:00-12:00, the
    rest of the NY a.m. session).
  * null = the same signed distance from price, same side, same 120 bars, at 10:00 NY on
    a random other day within +/-30 days (clock held fixed: the claim is about the
    unmet-by-10:00 state, not about 10:00-12:00 volatility).
  * claim '-': the unmet objective is reached LESS often than the matched null.

Reading b (claim '+') — "Expect a retracement at the flip of a new 4-hour candle when
the prior 4-hour expanded" on his 18/22/02/06/10/14 grid (futures grid).
  * prior 4H candle (futures grid) with body != 0 and opposing run (open -> extreme
    against the body) / |body| <= 1.0 (expansion candle, threshold_fits grade A).
  * at the next candle's open T (= prior close_time; the 18:00 reopen flip excluded:
    it follows the daily halt, a gap artefact), hit = price trades back to the prior
    candle's body midpoint (0.5 of the body) within the first 60 M1 bars.
  * null = the same signed distance from price, same side, same 60 bars, at the same NY
    clock time on a random other day within +/-30 days.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ny_dates, at_ny, utc_ns, empty, ny_mod  # noqa: E402

CID = "ten-am-candle-alignment"
HORIZON_A = 120
HORIZON_B = 60
WICK_CUT = 1.0


# ── reading a ────────────────────────────────────────────────────────────────
def detect_a(m1):
    cols = ["decision_time", "available_at", "direction", "target_px"]
    if len(m1) < 2000:
        return empty(cols)
    mkt = cl.get_market(m1)
    dates = ny_dates(m1)
    t930, t10, t830 = at_ny(dates, "09:30"), at_ny(dates, "10:00"), at_ny(dates, "08:30")
    ok = ~pd.isna(t930) & ~pd.isna(t10)
    t930, t10, t830 = t930[ok], t10[ok], t830[ok]
    i9 = np.searchsorted(mkt.tn, utc_ns(t930), side="left")
    i10 = np.searchsorted(mkt.tn, utc_ns(t10), side="left")
    i8 = np.searchsorted(mkt.tn, utc_ns(t830), side="left")
    has = ((i10 - i9) >= 25) & ((i9 - i8) >= 45) & (i10 <= len(mkt.tn)) & (i9 >= 1)
    t930, t10, i9, i10 = t930[has], t10[has], i9[has], i10[has]
    if len(t10) == 0:
        return empty(cols)
    ref = mkt.c[i9 - 1]
    pd_ = cl.prior_hilo(t930, "1D", m1=m1, min_coverage=0.5)
    run = cl.running_hilo(t930, "1D", m1=m1)
    pdh, pdl = pd_["high"].to_numpy(float), pd_["low"].to_numpy(float)
    rh, rl = run["high"].to_numpy(float), run["low"].to_numpy(float)
    up_ok = np.isfinite(pdh) & np.isfinite(rh) & (rh < pdh)
    dn_ok = np.isfinite(pdl) & np.isfinite(rl) & (rl > pdl)
    du = np.where(up_ok, pdh - ref, np.inf)
    dd = np.where(dn_ok, ref - pdl, np.inf)
    long_ = up_ok & (du <= dd)
    short = dn_ok & ~long_
    hi_930 = np.array([mkt.h[a:b].max() for a, b in zip(i9, i10)])
    lo_930 = np.array([mkt.l[a:b].min() for a, b in zip(i9, i10)])
    unmet = np.where(long_, hi_930 < pdh, np.where(short, lo_930 > pdl, False))
    keep = (long_ | short) & unmet
    out = pd.DataFrame({"decision_time": t10[keep], "available_at": t10[keep],
                        "direction": np.where(long_, 1, -1)[keep],
                        "target_px": np.where(long_, pdh, pdl)[keep]})
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


# ── reading b ────────────────────────────────────────────────────────────────
def detect_b(m1):
    cols = ["decision_time", "available_at", "direction", "level_px"]
    b = cl.build_bars(m1, "4h", grid4h="futures")
    if len(b) < 3:
        return empty(cols)
    ct = pd.DatetimeIndex(b["close_time"])
    i = np.arange(len(b))                                      # prior candle
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    body = c[i] - o[i]
    sgn = np.sign(body)
    opp = np.where(sgn > 0, o[i] - l[i], h[i] - o[i])
    exp_ = (sgn != 0) & (opp <= WICK_CUT * np.abs(body))
    T = ct[i]
    not18 = ny_mod(T) != 18 * 60
    k = exp_ & not18
    out = pd.DataFrame({"decision_time": T[k], "available_at": T[k],
                        "direction": sgn[k].astype(int),
                        "level_px": ((o[i] + c[i]) / 2.0)[k]})
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


def clock_null(t, level_dist, side, horizon):
    mkt = cl.get_market()
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS,
                         seed=cl.rules.SEED, tod_tol_min=0)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        if ok.any():
            p = mkt.pos_at_or_after(tk[ok])
            px = mkt.o[np.minimum(p, len(mkt.o) - 1)]
            lv = px + level_dist[ok]
            s = side[ok]
            r = np.full(ok.sum(), np.nan)
            for sd in ("above", "below"):
                m = s == sd
                if m.any():
                    r[m] = cl.touch(tk[ok][m], lv[m], sd,
                                    horizon_bars=horizon)["hit"].to_numpy(float)
            out[ok] = r
        return out
    return null_fn


def rate(ev, level_col, side, horizon, claim):
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    lv = ev[level_col].to_numpy(float)
    p = mkt.pos_at_or_after(t)
    px = mkt.o[np.minimum(p, len(mkt.o) - 1)]
    dist = lv - px
    obs = np.full(len(t), np.nan)
    for sd in ("above", "below"):
        m = side == sd
        obs[m] = cl.touch(t[m], lv[m], sd, horizon_bars=horizon)["hit"].to_numpy(float)
    null_fn = clock_null(t, dist, side, horizon)
    return cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                        null_fn=null_fn, predictors=ev, claim=claim)


def show(res):
    print({k: res.get(k) for k in ("n", "observed_rate", "null_rate", "lift", "diff",
                                   "ci_lo", "ci_hi", "p", "mde", "mde_threshold",
                                   "verdict", "verdict_detail", "halves")})


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        ev = cl.cache_frame("tenam_unmet_objective", lambda: detect_a(cl.load_m1()))
        print("a events", len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
        print("probe", probe.get("passed"))
        side = np.where(ev["direction"].to_numpy() > 0, "above", "below")
        res = rate(ev, "target_px", side, HORIZON_A, "-")
        show(res)
        op = {"rules": [
            "objective at 09:30 NY = previous trading day's high/low (18:00 roll, "
            "min_coverage 0.5) untaken this trading day, nearer to the 09:29 close",
            "row at 10:00 NY if the 09:30-09:59 M1 bars did not reach it",
            "hit = reached within the next 120 M1 bars (10:00-12:00)",
            "null = same signed distance/side/120 bars at 10:00 NY on a random other day "
            "within +/-30 days; claim '-' (consolidation: reached less often)"],
            "params": {"horizon_bars": HORIZON_A, "pd_min_coverage": 0.5,
                       "target_choice": "nearer untaken previous-day extreme",
                       "null_tod_tol_min": 0}}
        src = {"horizon_bars": "session_window_fit: NY a.m. window ends 12:00 "
                               "(08:30-12:00); declared-before-run",
               "pd_min_coverage": "declared-before-run: README trap 6, skip stub sessions",
               "target_choice": "corpus: tDiwwMRWF2k previous day low as the 9:30 target; "
                                "declared-before-run: nearer untaken one",
               "null_tod_tol_min": "declared-before-run: clock-fixed null so 10:00-12:00 "
                                   "volatility cancels (README trap 9)"}
        print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                              script=__file__, probe=probe,
                              notes="Reading a: the 10:00 deadline. Claim '-' = after an "
                                    "unmet 9:30 objective the target is reached less often "
                                    "than a clock-matched null at the same distance."))
    if "b" in which:
        ev = cl.cache_frame("tenam_4h_flip_retrace_futures", lambda: detect_b(cl.load_m1()))
        print("b events", len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_b, ev, lookback="10D")
        print("probe", probe.get("passed"))
        side = np.where(ev["direction"].to_numpy() > 0, "below", "above")
        res = rate(ev, "level_px", side, HORIZON_B, "+")
        show(res)
        op = {"rules": [
            "4H bars on the futures grid 18/22/02/06/10/14 NY",
            "prior candle expanded: body != 0 and opposing run / |body| <= 1.0",
            "at the next candle's open (18:00 reopen flip excluded): hit = price trades "
            "back to the prior body's midpoint within the first 60 M1 bars",
            "null = same signed distance/side/60 bars at the same NY clock on a random "
            "other day within +/-30 days"],
            "params": {"grid4h": "futures", "wick_cut": WICK_CUT, "horizon_bars": HORIZON_B,
                       "retrace_level": "0.5 of prior body", "exclude_flip": "18:00",
                       "null_tod_tol_min": 0}}
        src = {"grid4h": "corpus: EYzP7c24AwM '10:00 and 2:00 will be a 4-Hour candle' "
                         "(18/22/02/06/10/14 grid); phase3: grid carried as a knob",
               "wick_cut": "threshold_fits: small wick / expansion candle opposing_run/|body| "
                           "<= 1.0 (grade A)",
               "horizon_bars": "declared-before-run: 'on the flip' = the first hour of the "
                               "new 4H candle (measurable: 4H extremes within the first hour)",
               "retrace_level": "declared-before-run: 0.5 of the body (the corpus's 0.5 / "
                                "consequent-encroachment rule, threshold_fits 'shallow' cut)",
               "exclude_flip": "session_window_fit: the 18:00 reopen is a gap artefact",
               "null_tod_tol_min": "declared-before-run: clock-fixed null (README trap 9)"}
        print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                              script=__file__, probe=probe,
                              notes="Reading b: retracement at the 4H flip after an "
                                    "expansion candle, futures grid as the corpus states "
                                    "(gold's locked default is the forex grid)."))
