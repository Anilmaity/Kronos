"""risk_own_02a / gap-open-adr-budget — rate_test (claim '-').

"If we open right here, we could see 80 points ... If we open up with a gap up like that,
our 80 points become a lot harder to reach" (NESSCPMzWR0, gold, ADR ~80).
Claim: on a gap-open day the gap spends the budget, so a full ADR move from the open
AGAINST the gap (the target side in his example: gap up, target below) is reached LESS
often than the same distance from the open of an ordinary (non-gap) day.
  day        = 18:00 NY trading day with >= 600 M1 bars; previous day also real
  ADR        = mean H-L of the last 20 completed real days (as of the day open)
  gap g      = first M1 open of the day - close of the previous real day
  gap day    = |g| >= 0.25 * ADR
  observed   = price reaches open - sign(g) * ADR after the first M1 bar, within the day
  null       = a random NON-gap real day within +/-30 calendar days: does its price reach
               its own open -/+ the SAME absolute distance (ADR of the gap day), same
               direction, within its day (after its first M1 bar)
Pure level rule on daily open/close; no detector. Params declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a")
from _common import *   # noqa

ADR_LB = 20
GAP_CUT = 0.25
WINDOW_DAYS = 30


def day_table():
    m1 = cl.load_m1()
    d = cl.build_bars(m1, "1D")
    td = cl.trading_day(m1.index)
    g = pd.DataFrame({"td": td, "low": m1["low"].to_numpy(), "high": m1["high"].to_numpy()})
    g["k"] = g.groupby("td").cumcount()
    rest = g[g["k"] >= 1].groupby("td").agg(lo2=("low", "min"), hi2=("high", "max"))
    d = d.copy()
    d["td"] = cl.trading_day(pd.DatetimeIndex(d["first_m1"]))
    d = d.join(rest, on="td")
    d["real"] = d["n_m1"] >= MIN_N_M1
    rng = (d["high"] - d["low"]).where(d["real"])
    # ADR as of this day's open: mean of the previous 20 real days' ranges
    adr = rng.dropna().rolling(ADR_LB, min_periods=ADR_LB).mean().shift(1)
    d["adr"] = adr.reindex(d.index).ffill()
    # careful: ffill carries the value computed through the previous real day; for a real
    # day the shift(1) above already excludes itself.
    d.loc[d["real"], "adr"] = adr
    d["prev_close"] = d["close"].shift(1)
    d["prev_real"] = d["real"].shift(1, fill_value=False)
    d["gap"] = d["open"] - d["prev_close"]
    d = d[d["real"] & d["prev_real"] & d["adr"].notna() & d["lo2"].notna()].copy()
    d["gap_day"] = d["gap"].abs() >= GAP_CUT * d["adr"]
    d["t"] = pd.DatetimeIndex(d["first_m1"]) + pd.Timedelta(minutes=1)
    return d


if __name__ == "__main__":
    d = day_table()
    gd = d[d["gap_day"]].copy()
    ng = d[~d["gap_day"]].copy()
    print("days", len(d), "gap days", len(gd), "median |gap|/adr", (gd.gap.abs() / gd.adr).median())
    sgn = np.sign(gd["gap"].to_numpy())
    dist = gd["adr"].to_numpy(float)
    lvl = gd["open"].to_numpy(float) - sgn * dist
    # observed via the engine (first M1 bar excluded: scan starts at its close)
    obs = np.empty(len(gd), bool)
    up, dn = sgn < 0, sgn > 0      # gap down -> target above; gap up -> target below
    t = pd.DatetimeIndex(gd["t"])
    hb = gd["n_m1"].to_numpy() - 1
    if dn.any():
        obs[dn] = cl.touch(t[dn], lvl[dn], "below", horizon_bars=hb[dn])["hit"].to_numpy()
    if up.any():
        obs[up] = cl.touch(t[up], lvl[up], "above", horizon_bars=hb[up])["hit"].to_numpy()
    # cross-check with the per-day table
    chk = np.where(dn, gd["lo2"].to_numpy() <= lvl, gd["hi2"].to_numpy() >= lvl)
    print("engine vs table agreement", (chk == obs).mean())
    ng_t = cl.data.utc_ns(pd.DatetimeIndex(ng["t"]))
    ng_open, ng_lo, ng_hi = (ng[k].to_numpy(float) for k in ("open", "lo2", "hi2"))
    gt = cl.data.utc_ns(t)
    w = np.int64(WINDOW_DAYS * 86400 * 10**9)
    lo_i = np.searchsorted(ng_t, gt - w, "left")
    hi_i = np.searchsorted(ng_t, gt + w, "right")

    def null_fn(rng, k):
        j = lo_i + np.floor(rng.random(len(gt)) * (hi_i - lo_i)).astype(int)
        j = np.clip(j, 0, len(ng_t) - 1)
        return np.where(dn, ng_open[j] - ng_lo[j] >= dist, ng_hi[j] - ng_open[j] >= dist)

    assert (hi_i > lo_i).all()
    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="-")
    show(res)
    params = {"adr_lookback_days": ADR_LB, "adr_stat": "mean H-L of completed real days",
              "gap_cut_adr": GAP_CUT, "gap_ref": "previous real day's close",
              "target_distance": "1.0 x ADR from the day open, against the gap",
              "null": "random non-gap real day within +/-30 calendar days, same absolute distance, same direction, its own full day",
              "null_window_days": WINDOW_DAYS, "stub_day_min_n_m1": MIN_N_M1, "day_roll": "18:00 NY",
              "horizon": "rest of the trading day after the first M1 bar (horizon_bars)"}
    src = {"adr_lookback_days": "corpus: X4XSsv5CNqg (average-daily-range) 'a daily chart with at least the current month visible' -> ~20 trading days (declared-before-run, as in risk_own_01b)",
           "adr_stat": "corpus: NESSCPMzWR0 'maybe an 80-point range, let's just give that for the average daily range'",
           "gap_cut_adr": "declared-before-run: corpus gives no gap size ('large enough to be obvious'); 0.25 ADR",
           "gap_ref": "declared-before-run: gap = open vs previous close (the corpus measures the budget from the open)",
           "target_distance": "corpus: NESSCPMzWR0 'If we open right here, we could see 80 points ... with a gap up ... our 80 points become a lot harder to reach'",
           "null": "declared-before-run: measurable 'hit rate of the far target on gap-open days vs non-gap days'",
           "null_window_days": "phase3: locked +/-30-day regime window",
           "stub_day_min_n_m1": MIN_N_M1_SRC,
           "day_roll": "session_window_fit: settled 18:00 NY daily roll",
           "horizon": "corpus: NESSCPMzWR0 'are we still looking for this low in one day? No'"}
    op = {"rules": ["gap day: |first M1 open - previous real day close| >= 0.25 x ADR(20)",
                    "target = open - sign(gap) x ADR (a full ADR move from the open, against the gap)",
                    "observed: reached within the trading day, after the first M1 bar",
                    "null: same absolute distance and direction from the open of random non-gap days within +/-30d",
                    "claim -: the gap spends the budget, so gap days reach the ADR target less often"],
          "params": params}
    p = cl.write_result("gap-open-adr-budget", None, res, operationalization=op,
                        params_source=src, script=__file__,
                        no_detector="pure level rule: daily open, previous close and ADR from completed days (build_bars 1D), outcome via touch",
                        notes=("The rule's substitution step (pull the target to the previous day's "
                               "low) is a target choice, not a claim; the testable content is that a "
                               "full-ADR move from a gapped open is harder than from an ordinary open."))
    print("wrote", p)
