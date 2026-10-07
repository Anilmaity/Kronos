"""fomc-nfp-cpi-only -- update_20261007 (live_02/06/09/13 drafts, TTrades voice).

New claims (the prior unlabelled reading tested only the post-FOMC block):
  u1007a  whole-day skip (Hlwq1dRjBZo 'I avoid the day of CPI and ... NFP ... FOMC'):
          blocked = decision on the session date (18:00 NY roll) of an NFP or FOMC release.
  u1007b  no hold through / not right before (uW55Tuk-ngY 'not trade through or hold something
          intraday ... won't trade the session before or right prior to it'; wa9m30UHrm0 'Don't trade
          right before it'; h1ZQWWQDhKA 'I do not trade through NFP, CPI or FOMC'):
          blocked = decision whose 150-min hold window contains the release instant
          (decision < release <= decision + 150 min).
Gate on the phase-3 bare 15m CISD book (same baseline as the prior reading), claim '+'
(allowed beats blocked, control-adjusted). CPI is NOT in the calendar: no verified CPI date
dataset exists in the repo and the campaign does not type CPI dates from memory (same choice
as time_own_02a / risk_guest_02b); CPI days sit in the allowed arm, which attenuates toward 0.

AUDIT 2026-10-07 (vault-context re-run): _common.nfp_dates() misses the BLS early-January
deferral -- a rule date of Jan 2/3 is released one week later. In span that mislabelled 3 of 126
NFP days (2020-01-03 -> 01-10, 2025-01-03 -> 01-10, 2026-01-02 -> 01-09; event_gate.py
OVERRIDES_NFP carries 2025-01-10 and 2026-01-09). Corrected locally below (the shared _common is
left untouched so 2026-09-23 readings stay reproducible); cache key bumped to v2 because a
DatetimeIndex global is not part of the cache fingerprint.
"""
import sys, os
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_own_02b")
from _common import cl, np, pd, cisd_book, base_params, base_rule, summarize, FOMC, nfp_dates, ny_to_utc, ny_date

TF = "15min"
HOLD = pd.Timedelta("150min")
NFP = nfp_dates(2015, 2026)
NFP = NFP[NFP <= pd.Timestamp("2026-07-31")]
# BLS early-January deferral (see AUDIT note): Jan 2/3 rule date -> next Friday
NFP = pd.DatetimeIndex([d + pd.Timedelta(days=7) if (d.month == 1 and d.day <= 3) else d for d in NFP])
assert {"2020-01-10", "2025-01-10", "2026-01-09"} <= set(NFP.strftime("%Y-%m-%d"))
assert not {"2020-01-03", "2025-01-03", "2026-01-02"} & set(NFP.strftime("%Y-%m-%d"))
EVENT_DATES = NFP.union(FOMC)
RELEASES = ny_to_utc(NFP, 8, 30).union(ny_to_utc(FOMC, 14, 0)).sort_values()


def detect(m1):
    ev = cisd_book(m1, TF)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC").as_unit("ns")
    ev["allowed_a"] = ~np.asarray(ny_date(t).isin(EVENT_DATES))
    rel = RELEASES.as_unit("ns").asi8
    i = np.searchsorted(rel, t.asi8, side="right")          # first release strictly after decision
    nxt = np.where(i < len(rel), rel[np.minimum(i, len(rel) - 1)], np.iinfo(np.int64).max)
    ev["allowed_b"] = ~((nxt - t.asi8) <= HOLD.value)
    return ev


READINGS = {
    "u1007a": ("allowed_a", "blocked = decision on an NFP or FOMC session date (18:00 NY roll), whole day skipped",
               "corpus: Hlwq1dRjBZo 'The only thing I do news-wise is I avoid the day of CPI and NF NFP and NFP FOMC CPI same day'"),
    "u1007b": ("allowed_b", "blocked = decision whose 150-min hold window contains an NFP (08:30 NY) or FOMC (14:00 NY) release (no hold through / no entry right before)",
               "corpus: uW55Tuk-ngY 'volatile news events that I tend to not trade through or hold something intraday ... I just won't trade the session before or right prior to it'; wa9m30UHrm0 'Don't trade right before it'; window = book's own max hold"),
}

if __name__ == "__main__":
    ev = cl.cache_frame(f"u1007_fomc_nfp_{TF}_v2", lambda: detect(cl.load_m1()))
    print(len(ev), "events; blocked a", int((~ev.allowed_a).sum()), "b", int((~ev.allowed_b).sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    bp, bs = base_params(TF)
    for reading, (col, rule, src_rule) in READINGS.items():
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold="150min", claim="+")
        summarize(res)
        params = {**bp, "calendar": f"NFP (BLS rule + early-January deferral, {len(NFP)} dates to 2026-07) + FOMC scheduled statements ({len(FOMC)} dates 2016-01..2026-03); CPI absent",
                  "release_times": "NFP 08:30 NY, FOMC 14:00 NY", "block_rule": rule}
        src = {**bs,
               "calendar": "declared-before-run: FOMC/NFP calendars from time_own_02b/_common.py (typed before any run there), NFP corrected for the BLS early-January deferral (Jan 2/3 rule date -> +7d; event_gate.py OVERRIDES_NFP 2025-01-10, 2026-01-09); CPI omitted: no verified CPI dataset, not typed from memory",
               "release_times": "declared-before-run: official release times 08:30 ET (Employment Situation), 14:00 ET (FOMC statement)",
               "block_rule": src_rule}
        p = cl.write_result("fomc-nfp-cpi-only", reading, res,
                            operationalization={"rules": [base_rule(TF), rule, "allowed = all other decisions"], "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="AUDIT 2026-10-07: NFP calendar corrected (3 January dates were one week early in _common.nfp_dates). CPI releases are not blocked (no verified calendar) -> attenuates toward 0. FOMC dates after 2026-03 omitted. PMI/PPI/oil-inventory clauses not scored (no calendar; oil not traded). 'Session before' not mapped to clock; u1007b uses the book's 150-min hold as the 'right prior' window.")
        print(p)
