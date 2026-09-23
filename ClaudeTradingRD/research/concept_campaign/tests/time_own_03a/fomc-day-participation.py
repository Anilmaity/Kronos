"""fomc-day-participation — Trading on an FOMC / high-impact day (contested, mixed voice:
host TTrades vs guest NickDoesFutures in the same stream, tDiwwMRWF2k).

Readings (the YAML's own two, tested as stated):
  a  HOST: "trade before FOMC only if something is clean, but usually not"; default is to
     stand down on the FOMC day and wait for the following day. Claim ('+'): excluding
     the FOMC trading day improves the book -> gate_test(mask = not_fomc_day).
  b  GUEST: "show up and run the same process every day and take the setup if one
     appears" — days scratched off in advance "often turn out to have carried clean
     setups". Claim ('+'): the process's setups on FOMC days beat a matched random entry
     -> trade_test on the FOMC-day rows of the same book.

Baseline book (stated): the phase-3 rung-0 15m bare CISD (series_open, 2/2 swing,
max_wait 3, stop at the protected swing, 2R, 150-minute hold) — the entry TF the host
uses in New York (timeframes.ltf 15m) and the locked phase-3 configuration.

Event calendar: scheduled FOMC statement days (statement 14:00 NY), 2016 -> data end,
typed from the Federal Reserve's published meeting calendar. Unscheduled emergency
actions (2020-03-03, 2020-03-15) are excluded: the concept is about a SCHEDULED release.
The calendar is checked BEFORE any test is run (python ... diag): the 14:00-14:10 NY M1
range on each listed day against the median of the same window on the surrounding
non-listed weekdays (+/-30 days). The check is a diagnostic of recall, reported in notes.
An FOMC trading day = the 18:00-NY-roll session containing the 14:00 statement.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, OHLC, show, cisd_frame   # noqa: E402

CID = "fomc-day-participation"
READ = sys.argv[1] if len(sys.argv) > 1 else "a"

FOMC = """
2016-01-27 2016-03-16 2016-04-27 2016-06-15 2016-07-27 2016-09-21 2016-11-02 2016-12-14
2017-02-01 2017-03-15 2017-05-03 2017-06-14 2017-07-26 2017-09-20 2017-11-01 2017-12-13
2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19
2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11
2020-01-29 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17
""".split()
FOMC_DAYS = pd.DatetimeIndex(sorted(pd.Timestamp(x) for x in FOMC))
REL_UTC = pd.DatetimeIndex([(d + pd.Timedelta(hours=14)).tz_localize("America/New_York")
                            for d in FOMC_DAYS]).tz_convert("UTC")
FOMC_TDAY = pd.DatetimeIndex(cl.trading_day(REL_UTC)).tz_localize(None).normalize()
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "not_fomc_day"]


def detect(m1: pd.DataFrame, read: str = READ) -> pd.DataFrame:
    ev = cisd_frame(m1, "15min")
    if ev.empty:
        return pd.DataFrame(columns=COLS)
    dec = pd.DatetimeIndex(ev["decision_time"])
    td = pd.DatetimeIndex(cl.trading_day(dec)).tz_localize(None).normalize()
    fomc = np.asarray(td.isin(FOMC_TDAY))
    out = pd.DataFrame({"decision_time": dec, "available_at": dec,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                        "not_fomc_day": ~fomc})
    if read == "b":
        out = out[fomc]
    return out[COLS].reset_index(drop=True)


def diag() -> pd.DataFrame:
    m1 = cl.load_m1()
    mod = cl.ny_minute_of_day(m1.index)
    w = (mod >= 840) & (mod < 850)
    x = m1[w]
    day = pd.DatetimeIndex(cl.to_ny(x.index)).tz_localize(None).normalize()
    rng = (x["high"].groupby(day.values).max() - x["low"].groupby(day.values).min())
    rng.index = pd.DatetimeIndex(rng.index)
    rows = []
    for d0 in FOMC_DAYS:
        if d0 not in rng.index:
            rows.append((d0, np.nan, np.nan))
            continue
        nb = rng[(rng.index >= d0 - pd.Timedelta(days=30)) & (rng.index <= d0 + pd.Timedelta(days=30))
                 & ~rng.index.isin(FOMC_DAYS) & (rng.index.dayofweek < 5)]
        rows.append((d0, float(rng[d0] / nb.median()), float((nb < rng[d0]).mean())))
    return pd.DataFrame(rows, columns=["day", "ratio_vs_median", "pct_of_neighbours_below"])


if READ == "a":
    OP = {"rules": [
        "baseline: 15m bare CISD (series_open, 2/2 swing, max_wait 3), decide at the confirming "
        "bar close, stop = protected swing, target 2R, 150-minute hold",
        "FOMC trading day = the 18:00-NY-roll session containing a scheduled FOMC statement "
        "(14:00 NY); calendar typed from the Fed's published schedule, emergencies excluded",
        "gate: decision NOT on an FOMC trading day (host: stand down, wait for the next day)"],
        "params": {"tf": "15min", "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                   "min_series": 1, "rr": 2.0, "max_hold": "150min",
                   "calendar": "scheduled FOMC statement days 2016-2026", "release": "14:00 NY",
                   "excluded_span": "whole FOMC trading day"}}
else:
    OP = {"rules": [
        "book: 15m bare CISD (series_open, 2/2 swing, max_wait 3), decide at the confirming bar "
        "close, stop = protected swing, target 2R, 150-minute hold",
        "only rows whose decision falls on an FOMC trading day (18:00-NY-roll session holding a "
        "scheduled 14:00 NY statement) — the guest's 'run the process every day'",
        "trade_test vs matched random entries"],
        "params": {"tf": "15min", "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                   "min_series": 1, "rr": 2.0, "max_hold": "150min",
                   "calendar": "scheduled FOMC statement days 2016-2026", "release": "14:00 NY",
                   "excluded_span": "whole FOMC trading day"}}
SRC = {"tf": "corpus: timeframes.ltf [15m, 5m] (15m first listed); phase3 primary entry TF",
       "level_rule": "phase3: locked CISD level rule (first-candle open)",
       "swing": "phase3: locked swing fractal left=2,right=2",
       "max_wait": "phase3: locked max_wait=3",
       "min_series": "phase3: locked min_series=1",
       "rr": "phase3: locked 2R target (§1.12)",
       "max_hold": "phase3: 10 entry-TF bars (§1.13)",
       "calendar": "declared-before-run: Federal Reserve published FOMC meeting calendar "
                   "(statement day), scheduled meetings only",
       "release": "declared-before-run: FOMC statement time 14:00 ET (Fed practice since 2013)",
       "excluded_span": "corpus: tDiwwMRWF2k host 'no interest in trading FOMC ... rather wait "
                        "for the following day'"}

if __name__ == "__main__":
    if READ == "diag":
        dg = diag()
        pd.set_option("display.width", 200)
        print(dg.to_string())
        print("share ratio>2:", (dg["ratio_vs_median"] > 2).mean(),
              "share >= 90th pct of neighbours:", (dg["pct_of_neighbours_below"] >= 0.9).mean())
        sys.exit(0)
    ev = cl.cache_frame(f"fomc_15mcisd_{READ}_v1", lambda: detect(cl.load_m1()))
    print(READ, len(ev), ev["not_fomc_day"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    if READ == "a":
        res = cl.gate_test(ev, "not_fomc_day", mask_available_at="decision_time",
                           max_hold="150min")
    else:
        res = cl.trade_test(ev, max_hold="150min")
    show(res)
    dg = diag()
    note = (f"Calendar recall check (pre-test): {int((dg['pct_of_neighbours_below'] >= 0.9).sum())}/"
            f"{len(dg)} listed days have a 14:00-14:10 NY M1 range at or above the 90th percentile "
            f"of their +/-30-day non-listed weekday neighbours; median ratio "
            f"{dg['ratio_vs_median'].median():.2f}x. ")
    if READ == "a":
        note += ("Guest reading B (trade normally) is the complement claim and is tested separately "
                 "as reading b (trade_test on FOMC-day rows). ")
    note += "At ~84 FOMC days the FOMC arm's effective n (trading days) is structurally < 200."
    p = cl.write_result(CID, READ, res, operationalization=OP, params_source=SRC,
                        script=__file__, probe=probe, notes=note)
    print(p)
