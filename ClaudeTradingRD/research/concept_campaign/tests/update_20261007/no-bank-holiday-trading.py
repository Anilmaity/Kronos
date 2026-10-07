"""no-bank-holiday-trading -- update_20261007 (live_13 draft, TTrades voice, wa9m30UHrm0).

Source (viewer Q&A on an indices stream): "What is your idea for bank holiday days?"
-> "Uh I don't trade it. Do something else with my life."  No reason, no holiday list.
New concept (not in batches.json); no prior reading exists.

Gate on the phase-3 bare 15m CISD book (same baseline as no-monday-rule / fomc-nfp-cpi-only),
claim '+' = trades on normal sessions beat trades on bank-holiday sessions (control-adjusted).
Session = NY trading day rolling at 18:00 (cl.session_date): the session that mostly trades on
the holiday's calendar date. The source leaves "which holidays" open -> two pre-declared readings:
  u1007a  US bank holidays = Federal Reserve Bank holiday schedule (he is a US/NY-clock trader):
          pandas USFederalHolidayCalendar rules (New Year, MLK, Washington's Birthday, Memorial,
          Juneteenth from 2021, Independence, Labor, Columbus, Veterans, Thanksgiving, Christmas)
          with the Fed observance: Sunday -> Monday, Saturday -> NOT observed (banks open Friday).
  u1007b  UK (England & Wales) bank holidays (the viewer's phrase is British; London is gold's
          OTC hub): New Year, Good Friday, Easter Monday, Early May, Spring, Summer, Christmas,
          Boxing Day with substitute days, plus the 2020/2022/2023 moves and one-off holidays.

hold_basis = "bars" (declared before any run): a bar-count probe of the data (no outcomes) shows
US holiday sessions halt early at 13:00/14:30 NY (1,100-1,230 M1 vs 1,374 median), so a 150-min
wall-clock hold would truncate exactly the blocked arm's trades vs their full-session controls
(README trap 7). 150 trading minutes = 10 entry-TF bars, phase-3 §5.5.

VAULT-CONTEXT RERUN (2026-10-07, readings u1007va / u1007vb). The first run wrote u1007a/u1007b with
this same detector, calendars and settings. They are kept, not overwritten. Nothing was changed after
seeing them: the frame (events_fp) and hyp_key are identical, so the rerun adds no hypothesis. The
vault checks below are diagnostics only (no exclusions, no knob changes):
  - trap 5 / trap 7 (recompute from raw, cite the probe): the calendars were re-listed against the
    Fed/GOV.UK schedules, and the M1 feed was probed per holiday session. Christmas, New Year and
    UK Good Friday sessions have 0 bars, and Saturday US dates carry no session.
  - trap 6 (power before interpretation): usable blocked sessions = 86 US / 59 UK in the
    certified span, below the effective-n floor of 200, so neither reading can be EDGE or NULL
    whatever the outcomes. Only NEGATIVE / UNDERPOWERED / UNTESTABLE are reachable.
  - XAUUSD Data Inventory: the 2025-12-25 23:05-23:07 UTC reopen spike (~$45 wicks, present in M1)
    sits in the 2025-12-26 UK Boxing Day session (u1007vb blocked arm). Not excluded, which would be
    a post-hoc fork. Blocked trades whose hold spans it are counted and reported.
  - Session Timing / reopen gaps: blocked-arm decisions just before an early halt enter at the
    18:00 reopen. The share of entries more than 60 min after the decision is reported per arm.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_own_02b")
from _common import cl, np, pd, cisd_book, base_params, base_rule, summarize, ny_date  # noqa: E402
from pandas.tseries.holiday import (USFederalHolidayCalendar, Holiday, GoodFriday, EasterMonday,  # noqa: E402
                                    sunday_to_monday, next_monday, next_monday_or_tuesday, MO)
from pandas.tseries.offsets import DateOffset  # noqa: E402

CID = "no-bank-holiday-trading"
TF = "15min"
HOLD = "150min"
Y0, Y1 = "2015-12-01", "2026-12-31"


def us_bank_holidays():
    out = []
    for r in USFederalHolidayCalendar.rules:
        if r.offset is None:   # fixed-date rule: Fed observance (Sat not observed, Sun -> Mon)
            r = Holiday(r.name, month=r.month, day=r.day, start_date=r.start_date,
                        end_date=r.end_date, observance=sunday_to_monday)
        out.append(r.dates(Y0, Y1))
    return pd.DatetimeIndex(np.concatenate(out)).normalize().unique().sort_values()


def uk_bank_holidays():
    rules = [Holiday("New Year", month=1, day=1, observance=next_monday), GoodFriday, EasterMonday,
             Holiday("Early May", month=5, day=1, offset=DateOffset(weekday=MO(1))),
             Holiday("Spring", month=5, day=31, offset=DateOffset(weekday=MO(-1))),
             Holiday("Summer", month=8, day=31, offset=DateOffset(weekday=MO(-1))),
             Holiday("Christmas", month=12, day=25, observance=next_monday),
             Holiday("Boxing Day", month=12, day=26, observance=next_monday_or_tuesday)]
    d = set(pd.DatetimeIndex(np.concatenate([r.dates(Y0, Y1) for r in rules])).normalize())
    d -= {pd.Timestamp("2020-05-04"), pd.Timestamp("2022-05-30")}            # moved holidays
    d |= {pd.Timestamp(x) for x in ("2020-05-08", "2022-06-02", "2022-06-03",  # VE Day, Jubilee x2
                                    "2022-09-19", "2023-05-08")}              # State Funeral, Coronation
    return pd.DatetimeIndex(sorted(d))


US = us_bank_holidays()
UK = uk_bank_holidays()


def detect(m1):
    ev = cisd_book(m1, TF)
    sd = ny_date(pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC"))
    ev["allowed_us"] = ~np.asarray(sd.isin(US))
    ev["allowed_uk"] = ~np.asarray(sd.isin(UK))
    return ev


READINGS = {
    "u1007va": ("allowed_us", US,
               "blocked = decision on a US bank-holiday session (Federal Reserve holiday schedule; "
               "Sat holidays not observed, Sun -> Mon); session = 18:00 NY roll",
               "declared-before-run: 'bank holiday' read literally as the US Federal Reserve Bank holiday schedule "
               "(he trades the NY clock); corpus: wa9m30UHrm0 'Uh I don't trade it. Do something else with my life.'"),
    "u1007vb": ("allowed_uk", UK,
               "blocked = decision on a UK (England & Wales) bank-holiday session incl. substitute days, "
               "2020/2022 moves and 2022-06-03/2022-09-19/2023-05-08 one-offs; session = 18:00 NY roll",
               "declared-before-run: 'bank holiday' is the viewer's British phrase; London is gold's OTC hub "
               "(no LBMA auction on UK bank holidays); corpus: wa9m30UHrm0 'Uh I don't trade it. Do something else with my life.'"),
}

SPIKE = (pd.Timestamp("2025-12-25 23:05", tz="UTC"), pd.Timestamp("2025-12-25 23:08", tz="UTC"))


def diagnostics(res):
    """Vault checks on the scored trades (no filtering): halt-crossing entries per arm, spike exposure."""
    tr = res["_trades"]
    late = (pd.DatetimeIndex(tr["entry_time"]) - pd.DatetimeIndex(tr["decision_time"])) > pd.Timedelta("60min")
    blk = ~tr["gate"].to_numpy(bool)
    spike = ((pd.DatetimeIndex(tr["entry_time"]) < SPIKE[1]) & (pd.DatetimeIndex(tr["exit_time"]) >= SPIKE[0]))
    return {"late_entry_share_blocked": round(float(late[blk].mean()), 4),
            "late_entry_share_allowed": round(float(late[~blk].mean()), 4),
            "blocked_trades_spanning_2025-12-25_spike": int((spike & blk).sum())}


if __name__ == "__main__":
    ev = cl.cache_frame(f"u1007_nobankhol_{TF}_v1", lambda: detect(cl.load_m1()))
    sd = ny_date(pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC"))
    n_sess = {}
    for rd, (col, cal, _, _) in READINGS.items():
        b = ~ev[col]
        n_sess[rd] = sd[b.to_numpy()].nunique()
        # trap 6: the effective-n floor (200 days per arm) is decided by the calendar, before any outcome
        print(rd, "events", len(ev), "blocked", int(b.sum()), "blocked sessions", n_sess[rd],
              "calendar dates", len(cal), "| eff-n floor 200 reachable:", n_sess[rd] >= 200)
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    bp, bs = base_params(TF)
    for rd, (col, cal, rule, src_rule) in READINGS.items():
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD,
                           hold_basis="bars", claim="+", keep_trades=True)
        diag = diagnostics(res)
        res.pop("_trades")
        summarize(res)
        print("diagnostics", diag)
        params = {**bp, "calendar": f"{len(cal)} dates {Y0[:4]}..{Y1[:4]}", "block_rule": rule,
                  "session": "cl.session_date, 18:00 NY roll", "hold_basis": "bars"}
        src = {**bs, "calendar": src_rule, "block_rule": src_rule,
               "session": "method_spec: §1.4 New York + DST, day rolls at 18:00 NY (session_window_fit)",
               "hold_basis": "declared-before-run: holiday sessions halt early (13:00/14:30 NY; bar-count probe of the data, "
                             "no outcomes); wall-clock holds would truncate the blocked arm only (README trap 7); "
                             "phase3: §5.5 max hold = 10 entry-TF periods = 150 trading minutes"}
        p = cl.write_result(CID, rd, res,
                            operationalization={"rules": [base_rule(TF), rule, "allowed = all other decisions",
                                                          "claim '+' = allowed (non-holiday) beats blocked, control-adjusted"],
                                                "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="Vault-context rerun of u1007" + rd[-1] + " (same detector, calendars, settings and hyp_key; "
                                  "u1007" + rd[-1] + " kept). New concept (update_20261007_live_13), not in batches.json. "
                                  "Source is a one-line viewer Q&A on an indices stream with no holiday list and no reason; "
                                  "two calendars pre-declared. Probe of the M1 feed: Christmas/New Year (and UK Good Friday) "
                                  f"sessions have 0 bars. Blocked sessions with events = {n_sess[rd]} < 200 effective-n floor, "
                                  "so EDGE/NULL are unreachable by construction (vault trap 6). Diagnostics (no exclusions): "
                                  f"{diag}. The blocked arm's NY-clock mix differs (holiday sessions halt at 13:00 NY), and the "
                                  "default control is not time-of-day matched (README: a timing concept is tested as gate_test).",
                            allow_unknown_id=True)
        print(p)
