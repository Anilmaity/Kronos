"""economic-calendar-filter (contested, voice mixed; own-voice video hKCMqh0ZsY0 crediting AM
Trades, plus earlier own-voice recordings).  A calendar filter -> gate_test on the phase-3
bare 15m CISD book (150-minute hold).

No economic-calendar dataset exists in this workspace.  The one red-folder release whose
dates are mechanically derivable is NFP (BLS reference-week rule, _common.nfp_dates).  CPI and
FOMC are NOT typed in from memory (a fabricated calendar is worse than a narrow one): their
days stay in the non-news arm, which can only attenuate the differential toward 0.

(a) the three-tier filter + standing rules (hKCMqh0ZsY0): skip Mondays; do not trade before
    the week's first high-impact event; HIGH impact = avoid the day prior and the release,
    watch after.  With NFP as the high-impact event:
      blocked = decision on a Monday session (Sun 18:00 - Mon 17:00 NY), OR in an NFP week
                before the 08:30 NY release (covers 'day prior' and 'before the first
                high-impact event'), OR a trade whose 150-min hold spans the 08:30 release.
      allowed = everything else.  claim '+': allowed beats blocked.
(b) the earlier participation reading (0R61Y6Pn74Q 'Thursday is our first red folder News day
    of the week' ... 'my interest lies post 8:30'; no-news days skipped): baseline = events
    decided 08:30-17:00 NY on Tue-Fri sessions; gate = the session is an NFP (red-folder)
    day.  claim '+': post-release trades on news days beat the same clock on other days.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
from _common import (cl, cisd_book, nfp_dates, base_params, base_src, base_rule, HOLD,  # noqa: E402
                     show)

TF = "15min"
NFP = pd.DatetimeIndex(nfp_dates())
REL_NS = pd.DatetimeIndex([pd.Timestamp(d.date()).tz_localize("America/New_York") + pd.Timedelta(hours=8, minutes=30)
                           for d in NFP]).tz_convert("UTC").as_unit("ns").asi8
HOLD_TD = pd.Timedelta(HOLD[TF])


def _week(d):
    d = pd.DatetimeIndex(d)
    return (d - pd.to_timedelta(d.dayofweek, unit="D")).to_numpy()


def detect_a(m1):
    ev = cisd_book(m1, TF)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    tn = t.as_unit("ns").asi8
    sd = cl.session_date(t)                                  # Monday's session -> Monday
    monday = np.asarray(sd.dayofweek == 0)
    j = np.searchsorted(REL_NS, tn, side="left")             # next release at/after t
    ok = j < len(REL_NS)
    jj = np.clip(j, 0, len(REL_NS) - 1)
    same_week = _week(NFP[jj]) == _week(sd)
    pre = ok & same_week & (tn < REL_NS[jj])
    span = ok & (REL_NS[jj] <= (t + HOLD_TD).as_unit("ns").asi8) & (tn < REL_NS[jj])
    ev["allowed"] = ~(monday | pre | span)
    return ev


def detect_b(m1):
    ev = cisd_book(m1, TF)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    sd = cl.session_date(t)
    keep = cl.in_window(t, "08:30", "17:00") & np.asarray(sd.dayofweek.isin([1, 2, 3, 4]))
    ev = ev[keep].reset_index(drop=True)
    sd = cl.session_date(pd.DatetimeIndex(ev["decision_time"]))
    ev["news_day"] = np.asarray(sd.isin(NFP))
    return ev


if __name__ == "__main__":
    common_par = {**base_params(TF), "events": "NFP only", "release_time": "08:30 NY",
                  "nfp_rule": "3rd Friday after the Saturday ending the week containing the 12th of the prior month (+Jul/Jan and 2025-shutdown adjustments)",
                  "tz": "America/New_York"}
    common_src = {**base_src(TF, "corpus: economic-calendar-filter timeframes are 1W/1D (a day filter); 15m = phase-3 entry TF (his favourite 15m stack)"),
                  "events": "declared-before-run: only NFP is mechanically derivable; no calendar dataset; CPI/FOMC not typed from memory",
                  "release_time": "corpus: Zm2oKad3Tb8 'you can see we have high impact news at 8 30'",
                  "nfp_rule": "declared-before-run: BLS Employment Situation scheduling convention",
                  "tz": "method_spec: §1.4 DST settled, America/New_York"}
    for reading, det, col, key, rules, extra, extra_src in (
        ("a", detect_a, "allowed", "to02a_econ_a_15m",
         ["blocked = Monday session (session_date Monday), or NFP week before the 08:30 NY Friday release, or a trade whose 150-min hold spans that release",
          "allowed = everything else (non-NFP weeks' other releases unmodelled -> allowed)"],
         {"skip_monday": True},
         {"skip_monday": "corpus: hKCMqh0ZsY0 'as well as skipping Mondays'; 'I avoid trading prior to the first high impact news event of the week'; 'with high impact news I'm going to avoid the day prior avoid the release'"}),
        ("b", detect_b, "news_day", "to02a_econ_b_15m",
         ["baseline restricted to events decided in [08:30, 17:00) NY on Tue-Fri sessions",
          "gate news_day = the session date is an NFP release day (post-release by construction)"],
         {"window": "08:30-17:00 NY, Tue-Fri"},
         {"window": "corpus: 0R61Y6Pn74Q 'this is where my interest lies post 8:30 or after CPI'; 'Thursday is our first red folder News day of the week'"}),
    ):
        ev = cl.cache_frame(key, lambda: det(cl.load_m1()))
        print(reading, len(ev), "events; gate rate", ev[col].mean())
        probe = cl.probe_lookahead(det, ev, lookback="10D")
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD[TF])
        show(res)
        op = {"rules": [base_rule(TF),
                        "high-impact calendar = NFP dates only (rule-derived); CPI/FOMC days sit in the non-news arm"] + rules,
              "params": {**common_par, **extra}}
        print(cl.write_result("economic-calendar-filter", reading, res, operationalization=op,
                              params_source={**common_src, **extra_src}, script=__file__, probe=probe,
                              notes="Calendar restricted to NFP (only mechanically derivable red-folder release); unmodelled CPI/FOMC/other releases attenuate toward 0."))
