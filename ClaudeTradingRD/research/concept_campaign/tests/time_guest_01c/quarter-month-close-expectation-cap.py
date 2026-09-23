"""quarter-month-close-expectation-cap (guest: DayTradingRauf) -> rate_test.

Claim ('+'): in the closing week of a quarter (and month) "I wouldn't expect too much
from price" — realised range is smaller than in other weeks (the concept's measurable
"realised weekly range in month-end and quarter-end weeks vs other weeks").
Declared before the run:
  * Unit = one trading session (18:00 NY roll), so each row is its own outcome and the
    test has day-level power; a closing week contributes its (up to) five sessions.
  * Outcome = the session is a SMALL-range day: high-low < median range of the previous
    20 complete sessions (a regime-free, ATR-style normalisation known at the open).
    Stub sessions (< 600 M1 bars) are dropped as outcomes and from the trailing median.
  * Closing week = the Mon-Fri calendar week containing the last weekday of the month
    (pure calendar, known in advance).
    reading a: quarter-end closing weeks (Mar/Jun/Sep/Dec) — the case the guest states
               ("end of the quarter week and we are closing the monthly candle").
    reading b: any month-end closing week (concept ambiguity: month-end alone).
  * Null (matched, per row): the small-day rate among sessions within +/-30 calendar days
    that are NOT in a closing week of the tested kind — same normalisation, same regime.
  * Not tested: the "draw tagged then close back into the FVG" clause (no FVG anchor is
    specified for the monthly candle).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_guest_01c")
from _common import cl, np, pd, summary  # noqa: E402

CID = "quarter-month-close-expectation-cap"
LOOK, MIN_M1, WIN_D = 20, 600, 30


def build():
    d = cl.bars("1D")
    d = d[d["n_m1"] >= MIN_M1].copy()
    rng_ = (d["high"] - d["low"]).to_numpy()
    med = pd.Series(rng_).shift(1).rolling(LOOK, min_periods=LOOK).median().to_numpy()
    small = np.where(np.isfinite(med), (rng_ < med).astype(float), np.nan)
    sd = pd.DatetimeIndex(d["trading_day"]) + pd.Timedelta(days=1)       # session date
    wk = (sd - pd.to_timedelta(sd.dayofweek, unit="D")).normalize()
    months = pd.date_range(sd.min() - pd.offsets.MonthBegin(1), sd.max() + pd.offsets.MonthEnd(1), freq="BME")
    mw = (months - pd.to_timedelta(months.dayofweek, unit="D")).normalize()
    q_weeks = set(mw[months.month.isin([3, 6, 9, 12])])
    m_weeks = set(mw)
    out = pd.DataFrame({"t": pd.DatetimeIndex(d.index), "sd": sd, "small": small,
                        "q_close": np.array([w in q_weeks for w in wk]),
                        "m_close": np.array([w in m_weeks for w in wk])})
    return out.dropna(subset=["small"]).reset_index(drop=True)


def matched_null(df, flag):
    t = df["sd"].to_numpy().astype("datetime64[D]").astype(np.int64)
    s = df["small"].to_numpy()
    other = ~df[flag].to_numpy()
    cs_n = np.r_[0, np.cumsum(other)]
    cs_s = np.r_[0, np.cumsum(np.where(other, s, 0.0))]
    lo = np.searchsorted(t, t - WIN_D, side="left")
    hi = np.searchsorted(t, t + WIN_D, side="right")
    num, den = cs_s[hi] - cs_s[lo], cs_n[hi] - cs_n[lo]
    return np.where(den > 0, num / np.maximum(den, 1), np.nan)


if __name__ == "__main__":
    df = build()
    print(len(df), df["small"].mean(), df["q_close"].mean(), df["m_close"].mean())
    for reading, flag in (("a", "q_close"), ("b", "m_close")):
        nul = matched_null(df, flag)
        sel = df[flag].to_numpy()
        t = pd.DatetimeIndex(df["t"][sel])
        res = cl.rate_test(df["small"].to_numpy()[sel], t, available_at=t,
                           null=nul[sel], claim="+")
        print(reading, summary(res))
        op = {"rules": [
            "unit: one 18:00-NY trading session; outcome = range < median range of the prior "
            "20 complete sessions (stubs < 600 M1 bars dropped)",
            "closing week = Mon-Fri week containing the month's last weekday; reading a: "
            "quarter-end months only; reading b: every month",
            "null per row = small-day rate of sessions within +/-30 days outside such weeks"],
            "params": {"closing": "quarter" if reading == "a" else "month",
                       "trail_sessions": LOOK, "min_m1": MIN_M1, "null_window_days": WIN_D}}
        src = {"closing": ("corpus: qFtfD09Vv3E 'it is a end of the quarter week and we are closing the monthly candle'"
                           if reading == "a" else
                           "declared-before-run: concept ambiguity 'whether month-end alone triggers the same dampener'"),
               "trail_sessions": "declared-before-run: 20-session trailing median range (ATR-style unit, trap 6)",
               "min_m1": "declared-before-run: drop stub sessions (README trap 6)",
               "null_window_days": "declared-before-run: +/-30 days, the locked control regime window"}
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__,
                            no_detector="pure calendar rule: closing week from the calendar "
                                        "(last weekday of month/quarter); outcome from bars('1D')",
                            notes="Day-level rows (weekly effect measured on its sessions). "
                                  "The 'tag the draw then close back into the monthly FVG' clause "
                                  "is not tested.")
        print(p)
