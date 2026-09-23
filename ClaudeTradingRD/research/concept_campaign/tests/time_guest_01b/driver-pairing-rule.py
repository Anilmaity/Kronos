"""driver-pairing-rule (GxTradez, guest).

Claim: pair the day's reversal with a driver. If a reversal (a low/high of day at a key
level) is already in before the driver, the driver expands away from it; if none is in,
the driver itself reverses price from the key level.

Driver = 09:30 NY (the index open, 'a driver in itself, present every day'); 08:30/10:00
news drivers need a calendar and are not used. Key levels = prior trading day high/low.
Operationalisation (one trade book, both branches):
  A  reversal before the driver: by 09:30 the session has traded beyond exactly one of
     PDL/PDH and price (last close before 09:30) is back inside -> at 09:30 trade away from
     it (PDL swept -> long); stop = the session extreme so far (the reversal); 2R.
  B  no reversal before the driver: neither PDH nor PDL traded by 09:30; if within 15 min
     of the driver (09:30-09:45) price trades to PDH (PDL), fade it: decide at the close of
     the touching M1 bar, short (long); stop = level +/- 0.10 x prior-day range; 2R.
  Hold to 12:00 NY (150 min from the driver; wall clock from each decision capped there).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd

B_STOP_K = 0.10
RR = 2.0
WIN_MIN = 15


def detect(m1):
    ny = cl.to_ny(m1.index)
    mod = cl.ny_minute_of_day(m1.index)
    wd = ny.dayofweek
    # driver decision time: close of the 09:29 NY bar = 09:30
    d930 = m1.index[(mod == 9 * 60 + 29) & (wd < 5)] + pd.Timedelta(minutes=1)
    t = pd.DatetimeIndex(d930)
    ph = cl.prior_hilo(t, "1D", m1=m1, min_coverage=0.5)
    rh = cl.running_hilo(t, "1D", m1=m1)
    px = m1["close"].reindex(t - pd.Timedelta(minutes=1)).to_numpy()
    PDH, PDL = ph["high"].to_numpy(float), ph["low"].to_numpy(float)
    RH, RL = rh["high"].to_numpy(float), rh["low"].to_numpy(float)
    prng = PDH - PDL
    valid = np.isfinite(PDH) & np.isfinite(RH) & np.isfinite(px)
    sl, sh = RL < PDL, RH > PDH
    a_long = valid & sl & ~sh & (px > PDL)
    a_short = valid & sh & ~sl & (px < PDH)
    rows = []
    for i in np.nonzero(a_long | a_short)[0]:
        rows.append((t[i], 1 if a_long[i] else -1, RL[i] if a_long[i] else RH[i], "A"))
    # branch B
    nob = valid & ~sl & ~sh
    win = (mod >= 9 * 60 + 30) & (mod < 9 * 60 + 30 + WIN_MIN)
    wm = m1[win]
    wt = wm.index
    day_of = {tt.normalize(): i for i, tt in enumerate(cl.to_ny(t).tz_localize(None))}
    wkey = pd.DatetimeIndex(cl.to_ny(wt)).tz_localize(None).normalize()
    whi, wlo = wm["high"].to_numpy(), wm["low"].to_numpy()
    done = set()
    for j in range(len(wt)):
        i = day_of.get(wkey[j])
        if i is None or not nob[i] or i in done:
            continue
        up, dn = whi[j] >= PDH[i], wlo[j] <= PDL[i]
        if up == dn:          # neither, or both in one minute (ambiguous) -> keep scanning / skip
            if up:
                done.add(i)
            continue
        done.add(i)
        dt = wt[j] + pd.Timedelta(minutes=1)
        if up:
            rows.append((dt, -1, PDH[i] + B_STOP_K * prng[i], "B"))
        else:
            rows.append((dt, 1, PDL[i] - B_STOP_K * prng[i], "B"))
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "branch"])
    if ev.empty:
        return ev.assign(available_at=pd.Series(dtype="datetime64[ns, UTC]"), rr=RR, max_hold=pd.Series(dtype="timedelta64[ns]"))
    ev = ev.sort_values("decision_time").reset_index(drop=True)
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    end = cl.to_ny(pd.DatetimeIndex(ev["decision_time"])).normalize() + pd.Timedelta(hours=12)
    ev["max_hold"] = pd.DatetimeIndex(end).tz_convert("UTC") - pd.DatetimeIndex(ev["decision_time"])
    return ev[["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold", "branch"]]


if __name__ == "__main__":
    ev = cl.cache_frame("tg01b_driver930_pdhl", lambda: detect(cl.load_m1()))
    print(len(ev), ev["branch"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, claim="+")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": ["driver = 09:30 NY (index open, every weekday); key levels = prior trading-day high/low (18:00 NY roll, min_coverage 0.5)",
                    "A: by 09:30 exactly one of PDL/PDH traded and price back inside -> trade away from it at 09:30 (next M1 open), stop = session extreme so far, 2R",
                    "B: neither traded by 09:30; first M1 in 09:30-09:45 touching PDH/PDL -> fade at its close, stop = level +/- 0.10 x prior-day range, 2R (both in one minute -> skip)",
                    "exit by 12:00 NY"],
          "params": {"driver": "09:30 NY", "key_level": "PDH/PDL", "min_coverage": 0.5, "rr": RR,
                     "b_window_min": WIN_MIN, "b_stop": "0.10 x prior-day range beyond level", "exit": "12:00 NY"}}
    src = {"driver": "corpus: J_EeS2_2CAM yaml '9:30 index open (a driver in itself, present every day)'",
           "key_level": "declared-before-run: 'a key level for the day' unspecified; prior-day extremes are the standard daily key levels",
           "min_coverage": "declared-before-run: README trap 6 stub-session guard",
           "rr": "phase3: locked 2R target (conjunction_preregistration §1.8-1.13)",
           "b_window_min": "corpus: yaml measurable 'day's extreme is set within 15 minutes of a driver'",
           "b_stop": "declared-before-run: no stop stated; small ATR-unit buffer beyond the key level",
           "exit": "session_window_fit: corpus 'I only look to take trades between 8:30 and 12'"}
    p = cl.write_result("driver-pairing-rule", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="08:30/10:00 news drivers not identifiable without an economic calendar; 09:30 index open used as the every-day driver on XAUUSD.")
    print(p)
