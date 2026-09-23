"""no-monday-rule (contested, mixed voice): 'I never trade Mondays' / 'Monday is data'.

Gate tests on the phase-3 bare 15m CISD book (hold 150 min), claim '+' = the allowed arm
beats the blocked arm (control-adjusted). Monday = the NY trading day that rolls at 18:00
(the Sunday-evening reopen belongs to Monday).

reading a  -- plain rule (his own voice, wrIZ7CAuFCc / hKCMqh0ZsY0):
              allowed = decision on a Tue..Fri trading day; blocked = Monday.
reading b  -- AM Trades form (wGYde-h84cs): Monday blocked; Tuesday allowed ONLY if Monday
              engaged a higher-timeframe PD array, else Tuesday blocked too; Wed..Fri allowed.
              'Monday engaged a HTF PD array' is declared as: Monday's trading-day range traded
              through the prior completed week's high or low (PWH/PWL = the HTF old-high/old-low
              liquidity array; the corpus gives no narrower definition). Knowable at Monday's
              close (17:00 NY), which is before every Tuesday decision.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params, base_rule, summarize

TF = "15min"
READING = sys.argv[1] if len(sys.argv) > 1 else "a"


def detect(m1):
    ev = cisd_book(m1, TF)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    td = pd.DatetimeIndex(cl.session_date(t))
    dow = np.asarray(td.dayofweek)
    ev["mask_at"] = t
    if READING == "a":
        ev["allowed"] = dow != 0
        return ev
    # reading b: Monday engagement of PWH/PWL, evaluated on the prior completed trading day
    pd1 = cl.prior_hilo(t, "1D", m1=m1)              # for a Tuesday event: Monday's session
    pw = cl.prior_hilo(pd.DatetimeIndex(pd1["available_at"]).tz_convert("UTC")
                       - pd.Timedelta(minutes=1), "1W", m1=m1)  # week completed before Monday
    mon_td = pd.DatetimeIndex(cl.session_date(pd.DatetimeIndex(pd1["period_start"]).tz_convert("UTC")))
    is_tue = dow == 1
    prev_is_mon = np.asarray(mon_td.dayofweek) == 0
    hi, lo = pd1["high"].to_numpy(float), pd1["low"].to_numpy(float)
    pwh, pwl = pw["high"].to_numpy(float), pw["low"].to_numpy(float)
    engaged = (hi > pwh) | (lo < pwl)
    valid = np.isfinite(hi) & np.isfinite(pwh)
    tue_ok = is_tue & prev_is_mon & valid & engaged
    # Tuesday whose prior session is not a Monday (holiday) -> treated as not engaged (blocked)
    ev["allowed"] = (dow >= 2) | tue_ok
    mask_at = np.where(is_tue, pd.DatetimeIndex(pd1["available_at"]).tz_convert("UTC").as_unit("ns").asi8,
                       t.as_unit("ns").asi8)
    ev["mask_at"] = pd.DatetimeIndex(pd.to_datetime(mask_at, utc=True))
    ev.loc[is_tue & ~valid, "mask_at"] = ev.loc[is_tue & ~valid, "decision_time"]
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"to02b_nomonday_{READING}_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), "events; allowed share", ev["allowed"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed") if isinstance(probe, dict) else probe)
    res = cl.gate_test(ev, "allowed", mask_available_at="mask_at", max_hold="150min", claim="+")
    summarize(res)
    bp, bs = base_params(TF)
    rules = [base_rule(TF), "Monday = NY trading day rolling at 18:00 (Sunday reopen belongs to Monday)"]
    params = dict(bp)
    src = dict(bs)
    if READING == "a":
        rules.append("allowed = decisions on Tue..Fri trading days; blocked = Monday")
    else:
        rules += ["Monday blocked; Tuesday allowed only if Monday's session high > prior completed week high or low < prior week low; Wed..Fri allowed",
                  "Tuesday after a holiday Monday (prior session not Monday) is blocked"]
        params["htf_pd_array"] = "prior completed week high/low (PWH/PWL)"
        src["htf_pd_array"] = "declared-before-run: corpus wGYde-h84cs 'Monday is data you can use to anticipate the profile'; PD array operationalised as the HTF old high/low"
    p = cl.write_result("no-monday-rule", READING, res,
                        operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Gate on the phase-3 15m CISD baseline; the concept is a day-of-week filter, so no time-of-day control matching.")
    print(p)
