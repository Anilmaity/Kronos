"""news-impact-tiering (AM Trades, guest) - contested; two readings.

a) Red-folder-only filter: find the FIRST red-folder USD driver of each week; accumulation
   before it, manipulation at/just before it, expansion after. Needs the full red-folder
   calendar (ISM, JOLTS, retail sales, CPI, PPI, GDP, PCE, claims ...) to know which event
   is first in each week. No economic calendar exists in this workspace and only NFP (BLS
   rule) and FOMC (published schedule) dates are derivable, so the first red-folder event
   cannot be identified -> UNTESTABLE (data we lack).

b) Three-tier: HIGH impact (CPI, FOMC press conference, NFP) shapes the WEEKLY range.
   rate_test: for each high-impact event with a derivable date (NFP 08:30 ET Friday; FOMC
   press conference 14:30 ET), hit = the week's high or low (session-date Mon-Fri week,
   18:00 NY roll) is printed on the event day between the release and 17:00 NY.
   Null = the same weekday and the same clock window in a randomly drawn week containing
   neither an NFP nor an FOMC press conference, within +/-13 weeks (geometry: identical
   window length and weekday position). CPI weeks cannot be excluded from the null
   (no dates) which can only attenuate the difference. Cluster = week.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, FOMC_PRESSER, nfp_dates, ny_to_utc

NULL_WEEKS = 13
MIN_COV = 0.5


def week_table(m1):
    sd = pd.DatetimeIndex(cl.session_date(m1.index))
    wk = (sd - pd.to_timedelta(sd.dayofweek, unit="D")).normalize()
    df = pd.DataFrame({"wk": wk, "h": m1["high"].to_numpy(), "l": m1["low"].to_numpy(),
                       "t": m1.index})
    g = df.groupby("wk")
    ih = g["h"].idxmax()
    il = g["l"].idxmin()
    out = pd.DataFrame({"t_hi": df.loc[ih.values, "t"].to_numpy(),
                        "t_lo": df.loc[il.values, "t"].to_numpy(),
                        "n": g.size()}, index=ih.index)
    out["t_hi"] = pd.DatetimeIndex(out["t_hi"]).tz_convert("UTC")
    out["t_lo"] = pd.DatetimeIndex(out["t_lo"]).tz_convert("UTC")
    out = out[out["n"] >= MIN_COV * out["n"].median()]
    return out


def hit(wt, wk, day, hh, mm):
    """Is the week's high or low printed on NY date `day` between hh:mm and 17:00?"""
    if wk not in wt.index:
        return np.nan
    a = ny_to_utc([day], hh, mm)[0]
    b = ny_to_utc([day], 17, 0)[0]
    r = wt.loc[wk]
    return float((a <= r["t_hi"] < b) or (a <= r["t_lo"] < b))


if __name__ == "__main__":
    here = __file__
    cl.write_untestable(
        "news-impact-tiering",
        "reading a needs the identity of the FIRST red-folder USD event of every week; no economic calendar exists in the workspace and only NFP (BLS rule) and FOMC (published schedule) are derivable, while ISM/JOLTS/retail sales/CPI/PPI/GDP/PCE/claims dates are not - the first driver of a week cannot be located from OHLC",
        reading="a", script=here,
        notes="Reading b (three-tier, high impact shapes the weekly range) is tested on NFP+FOMC.")

    m1 = cl.load_m1()
    wt = week_table(m1)
    rows = []
    for d in nfp_dates():
        rows.append((d, 8, 30, "NFP"))
    for d in FOMC_PRESSER:
        rows.append((d, 14, 30, "FOMC"))
    ev = pd.DataFrame(rows, columns=["day", "hh", "mm", "kind"])
    ev["wk"] = ev["day"] - pd.to_timedelta(ev["day"].dt.dayofweek, unit="D")
    ev = ev[ev["wk"].isin(wt.index)].sort_values("day").reset_index(drop=True)
    ev_weeks = set(ev["wk"])
    ev["t"] = [ny_to_utc([r.day], r.hh, r.mm)[0] for r in ev.itertuples()]
    obs = np.array([hit(wt, r.wk, r.day, r.hh, r.mm) for r in ev.itertuples()])
    pool = pd.DatetimeIndex([w for w in wt.index if w not in ev_weeks])
    cand = [pool[np.abs((pool - w).days) <= 7 * NULL_WEEKS] for w in ev["wk"]]

    def null_fn(rng, k):
        out = np.full(len(ev), np.nan)
        for i, r in enumerate(ev.itertuples()):
            c = cand[i]
            if len(c) == 0:
                continue
            w = c[rng.integers(len(c))]
            day = w + pd.Timedelta(days=int(r.day.dayofweek))
            out[i] = hit(wt, w, day, r.hh, r.mm)
        return out

    t = pd.DatetimeIndex(ev["t"])
    print(len(ev), ev["kind"].value_counts().to_dict(), "obs rate", np.nanmean(obs))
    for kind in ("NFP", "FOMC"):
        s = ev["kind"] == kind
        print(kind, np.nanmean(obs[s]))
    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="+",
                       cluster=ev["wk"].astype(str).to_numpy(), outcome_horizon="5D")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "dependence"):
        print(k, res.get(k))
    op = {"rules": ["high-impact events with derivable dates: NFP (BLS rule, 08:30 ET) and FOMC press conference (14:30 ET, published schedule); CPI dates unavailable",
                    "week = session-date Mon-Fri week (18:00 NY roll); weeks with < 0.5 x median M1 count skipped",
                    "hit = the week's high or low (first M1 printing it) falls on the event's NY date between the release time and 17:00 NY",
                    "null = same weekday and clock window in a random week with no NFP and no FOMC presser, within +/-13 weeks; cluster = week"],
          "params": {"events": "NFP + FOMC presser", "window": "release -> 17:00 NY same day",
                     "null_weeks": NULL_WEEKS, "min_week_coverage": MIN_COV}}
    src = {"events": "corpus: QmGJFxfSHxM yaml 'High impact - exactly three events: CPI; the FOMC press conference; non-farm payroll' (CPI not derivable)",
           "window": "corpus: yaml measurable 'how often the weekly high or low is set on a high-impact-event day'; post-release part of the day declared-before-run",
           "null_weeks": "declared-before-run: nearby non-event weeks (+/-13 weeks ~ one quarter) to match regime",
           "min_week_coverage": "declared-before-run: README trap 6 stub guard"}
    p = cl.write_result("news-impact-tiering", "b", res, operationalization=op, params_source=src,
                        script=here, no_detector="pure calendar rule: event dates from the BLS NFP rule and the published FOMC schedule; outcomes are weekly extreme times from M1",
                        notes=f"per-kind observed rates: NFP {np.nanmean(obs[(ev['kind']=='NFP').to_numpy()]):.3f}, FOMC {np.nanmean(obs[(ev['kind']=='FOMC').to_numpy()]):.3f}. FOMC calendar verified by 14:00 NY volatility spike on all 69 dates before testing. Medium/low tiers untested (no calendar).")
    print(p)
