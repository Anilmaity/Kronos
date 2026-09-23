"""pre-event-avoidance-rule (AM Trades, guest): in a week with a high-impact release, avoid
every day before it; trade the days after; never enter before / hold through the release.

No economic-calendar dataset exists in this workspace. The one high-impact release whose
schedule is mechanically derivable is Non-Farm Payrolls (the concept's own worked example is
'Thursday before Friday NFP'). NFP date = BLS Employment Situation rule: the third Friday after
the Saturday that ends the reference week (the Sun-Sat week containing the 12th of the prior
month); if that Friday is Jan 1 or Jul 4 (observed), the Thursday before (Jul) / the next
Friday (Jan). 2025 government-shutdown releases are special-cased from the public record
(Sep-2025 report 2025-11-20, Oct report none, Nov report 2025-12-16).
FOMC and CPI dates are NOT typed in from memory (a fabricated calendar is worse than a narrow
one); those weeks stay in the allowed arm, which can only attenuate the differential.

Gate on the baseline 1h CISD book (claim '+'):
  blocked = decision on a trading day (18:00 NY roll) of an NFP week that precedes the NFP
            trading day, or on the NFP day before 08:30 NY; also any trade whose 10h hold
            window would span the 08:30 NY release.
  allowed = everything else.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, BASE_PARAMS, BASE_SRC, BASE_RULE

HOLD = pd.Timedelta("10h")


def nfp_dates(y0=2015, y1=2026):
    out = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            ry, rm = (y, m - 1) if m > 1 else (y - 1, 12)
            d12 = pd.Timestamp(ry, rm, 12)
            sat = d12 + pd.Timedelta(days=(5 - d12.dayofweek) % 7)
            fri = sat + pd.Timedelta(days=20)
            if fri.month == 7 and fri.day in (3, 4):
                fri = fri - pd.Timedelta(days=1)
            if fri.month == 1 and fri.day == 1:
                fri = fri + pd.Timedelta(days=7)
            out.append(fri.normalize())
    s = set(out)
    for bad in ("2025-10-03", "2025-11-07", "2025-12-05"):
        s.discard(pd.Timestamp(bad))
    s.update({pd.Timestamp("2025-11-20"), pd.Timestamp("2025-12-16")})
    return sorted(s)


NFP = nfp_dates()
REL_UTC = pd.DatetimeIndex([pd.Timestamp(d.date()).tz_localize("America/New_York")
                            + pd.Timedelta(hours=8, minutes=30) for d in NFP]).tz_convert("UTC")


def detect(m1):
    ev = cisd_book(m1)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    td = pd.DatetimeIndex(cl.trading_day(t)).tz_localize(None).normalize()
    rel_day = pd.DatetimeIndex([r.tz_convert("America/New_York").tz_localize(None).normalize()
                                for r in REL_UTC])
    blocked = np.zeros(len(ev), bool)
    # pre-event days of the release's week (Mon..day before) and the release day before 08:30
    rn = REL_UTC.as_unit("ns").asi8
    tn = t.as_unit("ns").asi8
    j = np.searchsorted(rn, tn, side="left")           # next release at/after t
    ok = j < len(rn)
    jj = np.clip(j, 0, len(rn) - 1)
    nxt_day = rel_day[jj]
    same_week = (nxt_day - pd.to_timedelta(nxt_day.dayofweek, unit="D")) == \
                (td - pd.to_timedelta(td.dayofweek, unit="D"))
    before_release = tn < rn[jj]
    blocked |= ok & np.asarray(same_week) & before_release
    # never hold through: the hold window [t, t+10h] spans a release
    blocked |= ok & (rn[jj] <= (t + HOLD).as_unit("ns").asi8) & before_release
    ev["allowed"] = ~blocked
    return ev


if __name__ == "__main__":
    # calendar sanity check (diagnostic only, never used to alter the calendar)
    m1 = cl.load_m1()
    ny = cl.to_ny(m1.index)
    rng = (m1["high"] - m1["low"]).to_numpy()
    mod = cl.ny_minute_of_day(m1.index)
    at830 = pd.Series(rng[mod == 510], index=pd.DatetimeIndex(ny[mod == 510]).tz_localize(None).normalize())
    med = at830.rolling(40, min_periods=10).median()
    nd = [d for d in NFP if d in at830.index]
    ratio = (at830 / med).reindex(nd)
    print("NFP 08:30 M1 range / rolling median: share >2x =", float((ratio > 2).mean()), "n", len(nd))
    ev = cl.cache_frame("rg02b_preevent_nfp_1hcisd", lambda: detect(cl.load_m1()))
    print(len(ev), "events; allowed share", ev["allowed"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "allowed", mask_available_at="decision_time", max_hold="10h", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [BASE_RULE,
                    "high-impact event = NFP only, dates from the BLS reference-week rule (+2025 shutdown special cases)",
                    "blocked = decision on a trading day of the NFP week before the NFP day, or on NFP day before 08:30 NY, or any trade whose 10h hold spans 08:30 NY on NFP day",
                    "allowed = everything else (FOMC/CPI weeks remain allowed: no calendar data)"],
          "params": {**BASE_PARAMS, "events": "NFP only", "release_time": "08:30 NY",
                     "nfp_rule": "3rd Friday after the Saturday ending the week containing the 12th of the prior month"}}
    src = {**BASE_SRC,
           "events": "declared-before-run: only NFP is mechanically derivable; corpus QmGJFxfSHxM example 'Thursday before Friday NFP'",
           "release_time": "method_spec/guest appendix: AM Trades concentrates on 08:30 releases",
           "nfp_rule": "declared-before-run: BLS Employment Situation scheduling convention"}
    p = cl.write_result("pre-event-avoidance-rule", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes=f"NFP calendar sanity: share of derived NFP days whose 08:30 NY M1 range exceeds 2x its 40-day rolling median = {float((ratio > 2).mean()):.2f} (n={len(nd)}); diagnostic only. FOMC/CPI weeks not gated (attenuates toward 0). Medium-impact intraday clause untested (no calendar).")
    print(p)
