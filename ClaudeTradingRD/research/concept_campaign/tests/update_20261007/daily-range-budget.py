"""daily-range-budget (ttrades) — update_20261007 drafts live_04 + edu_02, rate_test.

Prior reading (risk_own_02a, no label) gated a 15m CISD book on 'bulk consumed'. These
readings test only the NEW claims, as outcome rates (no trade book):

u1007a (live_04, session-consumption rule): 'if Asia forms a low here, London expands, do
  I expect much in New York? No ... if we don't use any range in the overnight session ...
  New York ... we expect to use the rest of the range'.
  Event = trading day, decided at the NY open (08:30 NY). consumed = overnight (18:00 NY ->
  08:30) H-L / expected range. Observed rows = days with consumed >= 0.80 ('used all the
  rope'); comparison (null) = days with consumed < 0.50 ('used little range'), 5 draws per
  row from +/-30 calendar days. Outcome = before the day closes (17:00 NY halt) price
  extends beyond the overnight high or low by >= 0.25 x expected range. Claim '-'.

u1007b (edu_02, half-the-range-left rule): 'our daily range of these expansion candles
  around 100 points, you know, we're halfway through it ... we still have a lot of range
  left'. Event = every 4H close inside the trading day (futures grid 22/02/06/10/14 NY).
  Observed rows = remaining = 1 - running H-L / expected >= 0.50; null = same 4H slot on
  days with remaining < 0.50, 5 draws from +/-30 days. Outcome = the day's range extends
  beyond the running high or low by >= 0.25 x expected before the day closes. Claim '+'.

Expected range (both): median H-L of the last 3 completed real days (as the prior reading;
corpus 0AYGNc9czYc reads three daily candles). All params declared before the first run.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                  # noqa: E402

CID = "daily-range-budget"
LOOKBACK = 3
MIN_N_M1 = 600
EXT = 0.25                     # extension (x expected range) that counts as 'more range'
REPS, WIN_DAYS = 5, 30         # locked phase-3 values
NY_OPEN_H = 14.5               # 08:30 NY = day open 18:00 + 14.5h
SLOTS_4H = (4, 8, 12, 16, 20)  # futures-grid 4H closes 22/02/06/10/14 NY, hours after 18:00
HI_CUT, LO_CUT = 0.80, 0.50


def _frame(m1, offsets_h):
    d = cl.build_bars(m1, "1D")
    real = d[d["n_m1"] >= MIN_N_M1]
    rng = (real["high"] - real["low"]).rolling(LOOKBACK, min_periods=LOOKBACK).median()
    rct = cl.data.utc_ns(pd.DatetimeIndex(real["close_time"]))
    start_ny = pd.DatetimeIndex(d.index).tz_convert("America/New_York")
    last = m1.index.max() + pd.Timedelta(minutes=1)
    rows = []
    for k, h in enumerate(offsets_h):
        t = (start_ny + pd.Timedelta(hours=h)).tz_convert("UTC")
        rows.append(pd.DataFrame({"day": pd.DatetimeIndex(d.index), "slot": k,
                                  "decision_time": t,
                                  "day_close": pd.DatetimeIndex(d["close_time"])}))
    ev = pd.concat(rows, ignore_index=True)
    ev = ev[(ev["decision_time"] < ev["day_close"]) & (ev["decision_time"] <= last)]
    ev = ev.sort_values("decision_time").reset_index(drop=True)
    t = pd.DatetimeIndex(ev["decision_time"])
    pos = np.searchsorted(rct, cl.data.utc_ns(t), side="right") - 1
    exp = np.where(pos >= 0, rng.to_numpy()[np.clip(pos, 0, None)], np.nan)
    run = cl.running_hilo(t, "1D", m1=m1)
    ev["expected"] = exp
    ev["run_hi"] = run["high"].to_numpy(float)
    ev["run_lo"] = run["low"].to_numpy(float)
    ev["consumed"] = (ev["run_hi"] - ev["run_lo"]) / ev["expected"]
    ev["available_at"] = ev["decision_time"]
    ok = np.isfinite(ev["consumed"]) & (ev["expected"] > 0)
    return ev[ok].reset_index(drop=True)


def all_a(m1):
    return _frame(m1, (NY_OPEN_H,))


def all_b(m1):
    return _frame(m1, SLOTS_4H)


def detect_a(m1):
    ev = all_a(m1)
    return ev[ev["consumed"] >= HI_CUT].reset_index(drop=True)


def detect_b(m1):
    ev = all_b(m1)
    return ev[ev["consumed"] <= 1 - LO_CUT].reset_index(drop=True)


def outcome(ev):
    t = pd.DatetimeIndex(ev["decision_time"])
    until = pd.DatetimeIndex(ev["day_close"])
    ext = EXT * ev["expected"].to_numpy()
    up = cl.touch(t, ev["run_hi"].to_numpy() + ext, "above", until=until)["hit"].to_numpy()
    dn = cl.touch(t, ev["run_lo"].to_numpy() - ext, "below", until=until)["hit"].to_numpy()
    return (up | dn).astype(float)


def matched_null(obs_ev, pool_ev, pool_out):
    """(n, REPS) outcomes of comparison-group rows: same slot, day within +/-WIN_DAYS."""
    rng = np.random.default_rng(cl.rules.SEED)
    out = np.full((len(obs_ev), REPS), np.nan)
    pday = pd.DatetimeIndex(pool_ev["day"]).asi8
    pslot = pool_ev["slot"].to_numpy()
    w = pd.Timedelta(days=WIN_DAYS).value
    oday = pd.DatetimeIndex(obs_ev["day"]).asi8
    for i, (dd, s) in enumerate(zip(oday, obs_ev["slot"].to_numpy())):
        cand = np.flatnonzero((pslot == s) & (np.abs(pday - dd) <= w))
        if len(cand):
            out[i] = pool_out[rng.choice(cand, REPS, replace=True)]
    return out


def run(reading, detect, allf, pool_sel, claim, rules, params, src):
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"drb_u1007_{reading}", lambda: detect(cl.load_m1()))
    alle = allf(m1)
    pool = alle[pool_sel(alle["consumed"].to_numpy())].reset_index(drop=True)
    print(reading, "events", len(ev), "pool", len(pool))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    obs = outcome(ev)
    null = matched_null(ev, pool, outcome(pool))
    t = pd.DatetimeIndex(ev["decision_time"])
    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null=null, predictors=ev, claim=claim)
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(" ", k, res.get(k))
    p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes=("Comparison group = the complementary consumption bucket on nearby days "
                               "(regime-matched by +/-30 days and same slot), passed as the null array. "
                               "Predictor known at decision: expected range from completed days, running "
                               "range from M1 closed by the decision. Outcome is day-level, day-block CI."))
    print("wrote", p)


COMMON_P = {"expected_range": f"median H-L of last {LOOKBACK} completed real days",
            "lookback_days": LOOKBACK, "day_open": "18:00 NY", "stub_day_min_n_m1": MIN_N_M1,
            "ext_frac": EXT, "outcome_window": "decision -> trading-day close",
            "null_reps": REPS, "null_window_days": WIN_DAYS}
COMMON_S = {
    "expected_range": "corpus: 0AYGNc9czYc 'from the high to the low, 658 points ... 740 ... 540 ... around 600, 500, 600 points' (median declared-before-run, as prior reading)",
    "lookback_days": "corpus: 0AYGNc9czYc worked example reads three daily candles",
    "day_open": "session_window_fit: settled 18:00 NY daily roll",
    "stub_day_min_n_m1": "declared-before-run: skip data-hole stub days (README trap 6)",
    "ext_frac": "declared-before-run: 9H15ZZvaKPQ 'We could sure expand a little more, but I'm not expecting price to just go send up here' -> 'much' NY range read as a further >= 25% of the expected daily range",
    "outcome_window": "corpus: 9H15ZZvaKPQ 'use the rest of the range' (within the day)",
    "null_reps": "method_spec: locked reps=5",
    "null_window_days": "method_spec: locked window_days=30",
}

if __name__ == "__main__":
    which = sys.argv[1:] or ["u1007a", "u1007b"]
    if "u1007a" in which:
        run("u1007a", detect_a, all_a, lambda c: c < LO_CUT, "-",
            ["trading day (18:00 NY roll); decision at 08:30 NY (NY open)",
             "expected = median H-L of last 3 completed real days; consumed = overnight 18:00->08:30 H-L / expected",
             "observed rows: consumed >= 0.80; null: same-slot days with consumed < 0.50 within +/-30 d, 5 draws (seeded)",
             "outcome = price extends beyond overnight high or low by >= 0.25 x expected before the trading day closes",
             "claim -: high-consumption overnights see less NY expansion than low-consumption overnights"],
            {**COMMON_P, "ny_open": "08:30 NY", "hi_cut": HI_CUT, "lo_cut": LO_CUT},
            {**COMMON_S,
             "ny_open": "session_window_fit: SESSION_WINDOWS ny_am starts 08:30 NY; 9H15ZZvaKPQ 'We get to New York'",
             "hi_cut": "declared-before-run: 'we've already used all the range' = prior reading's bulk cut >= 80% (risk_own_02a)",
             "lo_cut": "corpus: tUbrCewFdCU 'we're halfway through it ... we still have a lot of range left' -> < 50% used = range left; 9H15ZZvaKPQ 'we don't use any range all in the overnight'"})
    if "u1007b" in which:
        run("u1007b", detect_b, all_b, lambda c: c > 1 - LO_CUT, "+",
            ["4H closes inside the trading day, futures grid (22/02/06/10/14 NY)",
             "expected = median H-L of last 3 completed real days; remaining = 1 - running day H-L / expected",
             "observed rows: remaining >= 0.50; null: same 4H slot on days with remaining < 0.50 within +/-30 d, 5 draws (seeded)",
             "outcome = the day extends beyond its running high or low by >= 0.25 x expected before the trading day closes",
             "claim +: with half or more of the range left the day still delivers range"],
            {**COMMON_P, "grid4h": "futures", "remaining_cut": LO_CUT},
            {**COMMON_S,
             "grid4h": "declared-before-run: tUbrCewFdCU example is gold futures (100 points), CME 4H opens 18/22/02/06/10/14 NY",
             "remaining_cut": "corpus: tUbrCewFdCU 'daily range of these expansion candles around 100 points, you know, we're halfway through it ... we still have a lot of range left'"})
