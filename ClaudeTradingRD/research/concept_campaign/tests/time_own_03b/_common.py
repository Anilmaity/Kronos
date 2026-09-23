"""Shared helpers for batch time_own_03b (time category, TTrades own voice).

- cisd_book: the phase-3 locked bare CISD rung-0 book (series_open, swing 2/2,
  max_wait 3, stop at the protected swing, 2R); baseline for the gate tests.
- Release calendar, declared BEFORE any test in this batch was run:
  * FOMC: every SCHEDULED meeting's statement day 2016-2026 (statement 14:00 NY),
    transcribed from federalreserve.gov/monetarypolicy/fomccalendars.htm (2021-2026)
    and fomchistorical2016/2017/2018/2020.htm (fetched 2026-09-23); 2019 per the
    same site (matches time_guest_01b's presser list). Unscheduled actions
    (2020-03-03, 2020-03-15) and the cancelled 2020-03-17/18 meeting excluded.
  * NFP: BLS Employment Situation rule (same rule as risk_guest_02b and
    time_guest_01b), release 08:30 NY.
  CPI is NOT included: no verifiable schedule in the workspace; CPI days stay in
  the 'no release' arm, which can only attenuate a differential.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

PH3 = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked rung-0 config)"
HOLDS = {"1h": "10h", "15min": "150min", "5min": "50min"}   # phase3: 10 entry-TF bars


def cisd_raw(m1, tf):
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    return b, ev


def cisd_book(m1, tf="1h"):
    b, ev = cisd_raw(m1, tf)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
    })


def base_params(tf):
    p = {"baseline": "bare CISD", "baseline_tf": tf, "level_rule": "series_open",
         "swing": "2/2", "max_wait": 3, "rr": 2.0, "max_hold": HOLDS[tf]}
    return p, {k: PH3 for k in p}


FOMC = pd.to_datetime([
    "2016-01-27", "2016-03-16", "2016-04-27", "2016-06-15", "2016-07-27", "2016-09-21",
    "2016-11-02", "2016-12-14",
    "2017-02-01", "2017-03-15", "2017-05-03", "2017-06-14", "2017-07-26", "2017-09-20",
    "2017-11-01", "2017-12-13",
    "2018-01-31", "2018-03-21", "2018-05-02", "2018-06-13", "2018-08-01", "2018-09-26",
    "2018-11-08", "2018-12-19",
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19", "2019-07-31", "2019-09-18",
    "2019-10-30", "2019-12-11",
    "2020-01-29", "2020-04-29", "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05",
    "2020-12-16",
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28", "2021-09-22",
    "2021-11-03", "2021-12-15",
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27", "2022-09-21",
    "2022-11-02", "2022-12-14",
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20",
    "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18",
    "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17",
    "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29",
])


def nfp_dates(y0=2016, y1=2026):
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
    return pd.DatetimeIndex(sorted(s))


NFP = nfp_dates()


def ny_to_utc(dates, hh, mm):
    return pd.DatetimeIndex([pd.Timestamp(d.date()).tz_localize("America/New_York")
                             + pd.Timedelta(hours=hh, minutes=mm) for d in dates]).tz_convert("UTC")


# release moments (UTC) and the NY trading day (18:00 roll) each falls in
RELEASES = pd.DataFrame({
    "release_utc": ny_to_utc(NFP, 8, 30).append(ny_to_utc(FOMC, 14, 0)),
    "kind": ["NFP"] * len(NFP) + ["FOMC"] * len(FOMC),
})


def _tday(times):
    td = pd.DatetimeIndex(cl.trading_day(pd.DatetimeIndex(times).tz_convert("UTC")))
    return (td.tz_localize(None) if td.tz is not None else td).normalize()


RELEASES["tday"] = _tday(RELEASES["release_utc"])


def release_flags(times, kinds=("NFP", "FOMC")):
    """Per decision time: (on_release_day, before_release_same_day, after_release_same_day).
    Pure calendar: the schedule is public in advance, so all flags are known at t."""
    t = pd.DatetimeIndex(times).tz_convert("UTC")
    td = _tday(t)
    r = RELEASES[RELEASES["kind"].isin(kinds)]
    rel = pd.Series(pd.DatetimeIndex(r["release_utc"]).to_numpy(), index=pd.DatetimeIndex(r["tday"]))
    rel = rel[~rel.index.duplicated(keep="first")]
    m = rel.reindex(td)
    on = m.notna().to_numpy()
    before = np.zeros(len(t), bool)
    after = np.zeros(len(t), bool)
    if on.any():
        tn = t.as_unit("ns").asi8
        rn = pd.DatetimeIndex(m.to_numpy()).as_unit("ns").asi8  # NaT rows masked by `on`
        before = on & (tn < rn)
        after = on & (tn >= rn)
    return on, before, after
