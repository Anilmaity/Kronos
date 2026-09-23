"""large-range-day-targeting (guest: AM Trades, QmGJFxfSHxM).

Claim: the three-step selection (calendar -> daily phase -> weekly profile) picks the
days that print a LARGE-RANGE TRENDING daily candle. rate_test on the realised
profile of selected days vs a regime-matched base rate (random other day +/-30d).

Selection of day s, decided at the close of the previous trading day (declared
before the first run):
  step 1 (calendar)  never Monday; not the Thursday before the first Friday of the
                     month (the day before NFP, approximated by the calendar rule).
                     CPI / FOMC dates are NOT available in this dataset -> the
                     "days after a high-impact event" preference is not modelled.
  step 2 (phase)     the previous day was not an expansion (|close-open| >= 0.5 x ADR20).
  step 3 (profile)   s is a remaining day of a confirmed weekly profile, as defined
                     in weekly-profile-alignment.py (profile_trades).
Outcome: day s range >= ADR20 (as of the previous close) AND |close-open| >= 0.5 x
its own range ("large-range trending day").
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _common import cl, daily, np, pd, regime_null_fn  # noqa: E402

_spec = importlib.util.spec_from_file_location("wpa", HERE / "weekly-profile-alignment.py")
wpa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wpa)

CID = "large-range-day-targeting"
EXP_BODY_ADR = 0.5
TREND_BODY_SHARE = 0.5


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "target_sdate"]
    d = daily(m1)
    if len(d) < 30:
        return pd.DataFrame(columns=cols)
    sel = sorted({x[0] for x in wpa.profile_trades(d)})
    if not sel:
        return pd.DataFrame(columns=cols)
    sd = pd.DatetimeIndex(d["sdate"]).as_unit("ns").asi8
    body = (d["close"] - d["open"]).abs().to_numpy()
    expn = body >= EXP_BODY_ADR * d["adr"].to_numpy()
    ct = pd.DatetimeIndex(d["close_time"])
    rows = []
    for s in pd.DatetimeIndex(sel):
        if s.dayofweek == 0:
            continue
        if s.dayofweek == 3 and (s + pd.Timedelta(days=1)).day <= 7:
            continue                                   # day before (approx.) NFP
        j = np.searchsorted(sd, s.as_unit("ns").value, side="left") - 1
        if j < 0 or sd[j] != (s - pd.Timedelta(days=1)).as_unit("ns").value:
            continue
        if np.isnan(d["adr"].iat[j]) or expn[j]:
            continue
        rows.append((ct[j], s))
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["decision_time", "target_sdate"])
    out.insert(1, "available_at", out["decision_time"])
    return out[cols]


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    d = daily(m1)
    rng_ = d["rng"].to_numpy()
    adr_prev = d["adr"].shift(1).to_numpy()
    body = (d["close"] - d["open"]).abs().to_numpy()
    y = ((rng_ >= adr_prev) & (body >= TREND_BODY_SHARE * rng_)).astype(float)
    y[np.isnan(adr_prev)] = np.nan
    # outcome of the NEXT row, stamped at each row's close (pool for the null)
    t_all = pd.DatetimeIndex(d["close_time"])
    y_next = np.append(y[1:], np.nan)
    nxt_sd = np.append(pd.DatetimeIndex(d["sdate"])[1:].as_unit("ns").asi8, 0)
    pos = np.searchsorted(t_all.as_unit("ns").asi8, pd.DatetimeIndex(ev["decision_time"]).as_unit("ns").asi8)
    obs = y_next[pos]
    same = nxt_sd[pos] == pd.DatetimeIndex(ev["target_sdate"]).as_unit("ns").asi8
    obs = np.where(same, obs, np.nan)                  # target day missing (holiday) -> dropped
    t = pd.DatetimeIndex(ev["decision_time"])
    null_fn = regime_null_fn(t, t_all, y_next)
    print("events", len(ev), "scored", int(np.isfinite(obs).sum()), "base rate", np.nanmean(y))
    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn, predictors=ev, claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "decision at the previous trading day's close (18:00 NY days, stubs < 600 M1 dropped) for target session day s",
        "step 1: s is Tue-Fri and not the Thursday before the first Friday of the month (pre-NFP, calendar approximation); CPI/FOMC not modelled (no calendar data)",
        "step 2: the previous day was not an expansion (|close-open| < 0.5 x ADR20)",
        "step 3: s is a remaining day of a weekly profile confirmed by the prior closes (weekly-profile-alignment.py definitions)",
        "outcome: day s range >= ADR20 and |close-open| >= 0.5 x its range",
        "null: the same outcome on a random other trading day within +/-30 days"],
        "params": {"exp_body_adr": EXP_BODY_ADR, "trend_body_share": TREND_BODY_SHARE, "large_range_adr": 1.0,
                   "adr_n": 20, "nfp_rule": "first Friday", "null_window_days": 30, "stub_min_m1": 600,
                   "day_open_hour": 18}}
    src = {"exp_body_adr": "declared-before-run: expansion day = body >= half an average day (as three-daily-profiles)",
           "trend_body_share": "declared-before-run: 'trending' = body at least half the day's range",
           "large_range_adr": "declared-before-run: 'large range' (never quantified, QmGJFxfSHxM) = at least the 20-day average",
           "adr_n": "declared-before-run: 20-day average daily range",
           "nfp_rule": "corpus: QmGJFxfSHxM 'non-farm payroll (first Friday)'",
           "null_window_days": "phase3: +/-30 day regime-matched control window",
           "stub_min_m1": "declared-before-run: README trap 6 stub sessions",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="Partial step 1: CPI/FOMC calendar dates are not in the dataset, so only "
                        "'never Monday' and the pre-NFP Thursday exclusion are applied.")
    print("wrote", p)
