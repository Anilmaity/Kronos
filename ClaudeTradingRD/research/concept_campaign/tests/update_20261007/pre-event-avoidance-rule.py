"""pre-event-avoidance-rule -- update_20261007 (live_08 draft, TTrades voice, K7XVj2w3CP4).

New claims only (the prior unlabelled reading tested the guest's NFP-week avoidance on 1h CISD):
  u1007a  daily-entry exception: 'if I'm entering on the daily chart, I'll hold through CPI NFP'.
          Book = phase-3 bare CISD on the 1D chart (decide at the daily close, 18:00 NY roll),
          hold 10 entry-TF periods = 14 calendar days (~10 trading days). Gate column
          `no_release` = no NFP 08:30 NY release inside (decision, decision + 14D]; the generic
          'never hold through' rule would skip the complement. claim '+' = skipping/avoiding
          release exposure helps on daily trades. The exception PREDICTS this is not EDGE
          (holding daily trades through NFP costs nothing); EDGE contradicts it, NULL is
          consistent with it. Planned window, not realised exposure (realised needs the future).
  u1007b  'don't trade right during the Fed announcement': bare 5m CISD book, blocked = decision in
          [14:00, 15:30] NY on an FOMC statement date (statement 14:00 + press conference
          14:30-15:30); claim '+' (allowed beats blocked).
CPI absent: no verified CPI calendar in the repo, not typed from memory -> CPI exposure sits in the
'no_release' arm, which can only attenuate.
"""
import sys
from pathlib import Path
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_own_02b")
from _common import cl, np, pd, cisd_book, FOMC, nfp_dates, ny_to_utc, ny_date, summarize, PH3

NFP = nfp_dates(2015, 2026)
NFP = NFP[NFP <= pd.Timestamp("2026-07-31")]
NFP_UTC = ny_to_utc(NFP, 8, 30).sort_values()
HOLD_D = pd.Timedelta("14D")
HOLD_5 = "50min"
RES = Path(__file__).resolve().parents[2] / "results"


def detect_daily(m1):
    ev = cisd_book(m1, "1D")
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC").as_unit("ns")
    rel = NFP_UTC.as_unit("ns").asi8
    i = np.searchsorted(rel, t.asi8, side="right")          # first release strictly after decision
    nxt = np.where(i < len(rel), rel[np.minimum(i, len(rel) - 1)], np.iinfo(np.int64).max)
    ev["no_release"] = ~((nxt - t.asi8) <= HOLD_D.value)
    return ev


def detect_fed(m1):
    ev = cisd_book(m1, "5min")
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    mod = np.asarray(cl.ny_minute_of_day(t))
    on_fomc = np.asarray(ny_date(t).isin(FOMC))
    ev["allowed"] = ~(on_fomc & (mod >= 14 * 60) & (mod <= 15 * 60 + 30))
    return ev


if __name__ == "__main__":
    base_rule = lambda tf, hold: (f"baseline book: phase-3 bare {tf} CISD (series_open level, 2/2 swings, max_wait 3), "
                                  f"decide at the confirming bar close, enter next M1 open, stop at protected swing, 2R, hold {hold}")
    bp = {"baseline": "bare CISD", "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": 2.0}
    bs = {k: PH3 for k in bp}

    # ---- u1007a: daily-entry trades held through NFP
    # written 2026-10-07 05:21 UTC (run 3e462c10); never overwrite a prior reading on re-run
    if not (RES / "pre-event-avoidance-rule__u1007a.json").exists():
        ev = cl.cache_frame("u1007_preevent_daily_nfp_v1", lambda: detect_daily(cl.load_m1()))
        print(len(ev), "daily events; release-in-window", int((~ev.no_release).sum()))
        probe = cl.probe_lookahead(detect_daily, ev, lookback="200D", recent="20D")
        res = cl.gate_test(ev, "no_release", mask_available_at="decision_time", max_hold="14D", claim="+")
        summarize(res)
        params = {**bp, "baseline_tf": "1D", "max_hold": "14D",
                  "calendar": f"NFP (BLS rule, {len(NFP)} dates to 2026-07); CPI absent",
                  "release_time": "NFP 08:30 NY",
                  "gate": "no_release = no NFP release in (decision, decision+14D]"}
        src = {**bs, "baseline_tf": "corpus: K7XVj2w3CP4 'if I'm entering on the daily chart, I'll hold through CPI NFP'",
               "max_hold": "phase3: §5.5 max hold = 10 entry-TF periods; 10 trading days = 14 calendar days (declared-before-run)",
               "calendar": "declared-before-run: NFP calendar from time_own_02b/_common.py; CPI omitted: no verified dataset, not typed from memory",
               "release_time": "declared-before-run: Employment Situation release 08:30 ET",
               "gate": "corpus: K7XVj2w3CP4 'I don't hold through CPI NFP unless I'm in a higher higher time frame trade'; window = book's own max hold"}
        p = cl.write_result("pre-event-avoidance-rule", "u1007a", res,
                            operationalization={"rules": [base_rule("1D", "14D"),
                                "gated arm = daily trades with no NFP release inside the planned hold window; complement = trades that would be held through NFP",
                                "claim '+' = avoiding release exposure helps; the daily-entry exception predicts NOT EDGE"], "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="Exception claims holding daily trades through NFP is fine, so EDGE here would contradict the claim and NULL is consistent with it. Planned 14D window, not realised exposure. CPI not in calendar (attenuates).")
        print(p)

    # ---- u1007b: no entries during the Fed announcement
    # written 2026-10-07 05:25 UTC (run 9d2bd281); guarded on re-run like u1007a
    if not (RES / "pre-event-avoidance-rule__u1007b.json").exists():
        ev = cl.cache_frame("u1007_preevent_fed_5m_v1", lambda: detect_fed(cl.load_m1()))
        print(len(ev), "5m events; blocked", int((~ev.allowed).sum()))
        probe = cl.probe_lookahead(detect_fed, ev, lookback="10D")
        res = cl.gate_test(ev, "allowed", mask_available_at="decision_time", max_hold=HOLD_5, claim="+")
        summarize(res)
        params = {**bp, "baseline_tf": "5min", "max_hold": HOLD_5,
                  "calendar": f"FOMC scheduled statements ({len(FOMC)} dates 2016-01..2026-03)",
                  "window": "14:00-15:30 NY on FOMC dates (statement + press conference)"}
        src = {**bs, "baseline_tf": "corpus: K7XVj2w3CP4 'if you're taking a three-minute entry ... Obviously, don't trade right during the Fed announcement'; nearest phase-3 book TF = 5min",
               "max_hold": PH3,
               "calendar": "declared-before-run: FOMC calendar from time_own_02b/_common.py",
               "window": "declared-before-run: 'right during the Fed announcement' = 14:00 ET statement through the 14:30-15:30 ET press conference"}
        p = cl.write_result("pre-event-avoidance-rule", "u1007b", res,
                            operationalization={"rules": [base_rule("5min", HOLD_5),
                                "blocked = decision in [14:00, 15:30] NY on an FOMC statement date", "allowed = all other decisions"],
                                "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="Blocked arm is small (FOMC days only). FOMC dates after 2026-03 omitted.")
        print(p)


# ======================================================================================
# Vault-context rerun (2026-10-07, second pass): u1007va / u1007vb. Morning readings above untouched.
# Declared BEFORE running, after reading the KronosVault research notes + Backtest Methodology Traps:
#  * Trap 7 ("never evaluated" must not look like "passed"; cite the probe, not memory/extent):
#    the time_own_02b FOMC list stops at 2026-03-18 while the certified data runs to 2026-07-23, so
#    u1007b scored the 2026-04-29 and 2026-06-17 statements as ALLOWED. Probe (5-min M1 range at
#    14:00 NY / median of the prior 20 non-FOMC days): >2x on all 81 listed dates, 2.75x / 10.1x on
#    those two -> added. Same probe at 08:30 NY on the rule-derived NFP dates 2020-01-03, 2025-01-03,
#    2026-01-02, 2026-02-06: 0.78-1.77x, vs 3.1-4.8x on 2020-01-10, 2025-01-10, 2026-01-09,
#    2026-02-11 -> BLS early-January shift (derived Jan 2/3 moves one week) + 2026-02-11 shutdown
#    delay. The probe reads volatility only, never trade outcomes.
#  * Concept-campaign lesson 3 / Session Timing on Gold (time of day moves R by itself): u1007vb
#    compares Fed-window entries with entries in the SAME 14:00-15:30 NY window on non-FOMC days,
#    so the gate isolates the announcement, not the clock slot.
#  * Trap 6 (power first): daily book ~370 trades / effective n ~180; Fed arm <= 83 FOMC days. Both
#    sit below the effective-n floor of 200, so EDGE/NULL are unreachable: only UNDERPOWERED or
#    NEGATIVE can come back. Run anyway, as declared.
def nfp_verified():
    s = {d + pd.Timedelta(days=7) if (d.month == 1 and d.day <= 3) else d for d in nfp_dates(2015, 2026)}
    s = (s - {pd.Timestamp("2026-02-06")}) | {pd.Timestamp("2026-02-11")}
    return pd.DatetimeIndex(sorted(s))


NFP_V = nfp_verified()
NFP_V = NFP_V[NFP_V <= pd.Timestamp("2026-07-31")]
NFP_V_UTC = ny_to_utc(NFP_V, 8, 30).sort_values()
FOMC_V = FOMC.append(pd.to_datetime(["2026-04-29", "2026-06-17"])).sort_values()


def detect_daily_v(m1):
    ev = cisd_book(m1, "1D")
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC").as_unit("ns")
    rel = NFP_V_UTC.as_unit("ns").asi8
    i = np.searchsorted(rel, t.asi8, side="right")          # first release strictly after decision
    nxt = np.where(i < len(rel), rel[np.minimum(i, len(rel) - 1)], np.iinfo(np.int64).max)
    ev["no_release"] = ~((nxt - t.asi8) <= HOLD_D.value)
    return ev


def detect_fed_v(m1):
    ev = cisd_book(m1, "5min")
    mod = np.asarray(cl.ny_minute_of_day(pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")))
    ev = ev[(mod >= 14 * 60) & (mod <= 15 * 60 + 30)].reset_index(drop=True)
    ev["allowed"] = ~np.asarray(ny_date(pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")).isin(FOMC_V))
    return ev


if __name__ == "__main__":
    probe_note = ("calendar probe (volatility only): FOMC 14:00 NY 5-min range >2x prior-20-day median on 83/83 dates; "
                  "NFP 08:30 NY: fixed dates 3.1-4.8x, remaining <2x: 2022-04-01 1.54, 2022-06-03 1.88, 2025-12-16 1.68 "
                  "(kept), 2026-04-03 Good Friday has no bars (kept: released while closed)")

    if not (RES / "pre-event-avoidance-rule__u1007va.json").exists():
        ev = cl.cache_frame("u1007v_preevent_daily_nfp_v2", lambda: detect_daily_v(cl.load_m1()))
        print(len(ev), "daily events; release-in-window", int((~ev.no_release).sum()))
        probe = cl.probe_lookahead(detect_daily_v, ev, lookback="200D", recent="20D")
        res = cl.gate_test(ev, "no_release", mask_available_at="decision_time", max_hold="14D", claim="+")
        summarize(res)
        params = {**bp, "baseline_tf": "1D", "max_hold": "14D",
                  "calendar": f"NFP verified ({len(NFP_V)} dates to 2026-07): BLS rule + early-January one-week shift + 2025/26 shutdown dates; CPI absent",
                  "release_time": "NFP 08:30 NY",
                  "gate": "no_release = no NFP release in (decision, decision+14D]"}
        src = {**bs, "baseline_tf": "corpus: K7XVj2w3CP4 'if I'm entering on the daily chart, I'll hold through CPI NFP'",
               "max_hold": "phase3: §5.5 max hold = 10 entry-TF periods; 10 trading days = 14 calendar days (declared-before-run)",
               "calendar": "declared-before-run: time_own_02b BLS rule; Jan 2/3 -> +7d and 2026-02-11 confirmed by 08:30 NY M1-range probe (vault trap 7: cite the probe); CPI omitted: no verified dataset",
               "release_time": "declared-before-run: Employment Situation release 08:30 ET",
               "gate": "corpus: K7XVj2w3CP4 'I don't hold through CPI NFP unless I'm in a higher higher time frame trade'; window = book's own max hold"}
        p = cl.write_result("pre-event-avoidance-rule", "u1007va", res,
                            operationalization={"rules": [base_rule("1D", "14D"),
                                "gated arm = daily trades with no NFP release inside the planned hold window; complement = trades that would be held through NFP",
                                "claim '+' = avoiding release exposure helps; the daily-entry exception predicts NOT EDGE",
                                "vault rerun of u1007a with the probe-verified NFP calendar (4 dates moved)"], "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="Exception claims holding daily trades through NFP is fine: EDGE contradicts it, NULL/UNDERPOWERED do not. "
                                  "Planned 14D window, not realised exposure (attenuates). CPI not in calendar (attenuates). "
                                  "Effective n < 200 by construction (trap 6). " + probe_note)
        print(p)

    if not (RES / "pre-event-avoidance-rule__u1007vb.json").exists():
        ev = cl.cache_frame("u1007v_preevent_fed_5m_sameclock_v2", lambda: detect_fed_v(cl.load_m1()))
        print(len(ev), "5m 14:00-15:30 events; blocked", int((~ev.allowed).sum()))
        probe = cl.probe_lookahead(detect_fed_v, ev, lookback="10D")
        res = cl.gate_test(ev, "allowed", mask_available_at="decision_time", max_hold=HOLD_5, claim="+")
        summarize(res)
        params = {**bp, "baseline_tf": "5min", "max_hold": HOLD_5,
                  "calendar": f"FOMC scheduled statements ({len(FOMC_V)} dates 2016-01..2026-06)",
                  "window": "14:00-15:30 NY (statement + press conference)",
                  "reference_arm": "same 14:00-15:30 NY window on non-FOMC session dates"}
        src = {**bs, "baseline_tf": "corpus: K7XVj2w3CP4 'if you're taking a three-minute entry ... Obviously, don't trade right during the Fed announcement'; nearest phase-3 book TF = 5min",
               "max_hold": PH3,
               "calendar": "declared-before-run: time_own_02b FOMC list + 2026-04-29, 2026-06-17, both confirmed by 14:00 NY M1-range probe (vault trap 7)",
               "window": "declared-before-run: 'right during the Fed announcement' = 14:00 ET statement through the 14:30-15:30 ET press conference",
               "reference_arm": "declared-before-run: vault Concept Campaign lesson 3 / Session Timing on Gold - hold the clock fixed so the gate isolates the announcement"}
        p = cl.write_result("pre-event-avoidance-rule", "u1007vb", res,
                            operationalization={"rules": [base_rule("5min", HOLD_5),
                                "book restricted to decisions in [14:00, 15:30] NY on every session date",
                                "blocked = FOMC statement date; allowed = non-FOMC dates (same clock window)",
                                "vault rerun of u1007b: calendar completed to the data end, reference arm clock-matched"],
                                "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="Blocked arm <= 83 FOMC days: EDGE/NULL unreachable (effective-n floor). Flat 0.04R cost: real FOMC-window "
                                  "spreads are wider, so a blocked-arm advantage is overstated, not understated. " + probe_note)
        print(p)
