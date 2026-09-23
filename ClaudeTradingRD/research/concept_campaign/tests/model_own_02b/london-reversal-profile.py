"""london-reversal-profile (model, TTrades own voice, contested).

London (02:00-05:00 NY) runs counter to the day's direction and makes the day's extreme,
changes the state of delivery there, and New York continues. Execution per the concept: NOT on
the London CISD — wait for New York's opposing run back toward London's order block, enter on
the New York continuation, stop beyond the New York opposing-run extreme, 2R.

Operationalisation (bullish; bearish mirrors):
  * London low == the day's low so far at 05:00 (low of 18:00-05:00 NY): London made the extreme.
  * London CISD: a 15m CISD (phase-3 config) bullish, extreme inside London and equal to the
    London low, confirmed by 08:30 NY.
  * NY entry: the first 5m bullish CISD with extreme and confirmation inside 08:30-12:00 NY whose
    extreme stays above the London low and with the London low still the day's low at the
    confirmation (the NY opposing run did not break London's extreme).
  * enter next M1 open, stop at the 5m protected swing (NY opposing-run extreme), 2R, flat 17:00 NY.
Contested readings:
  a — London's run must reach a relevant HTF PD array: London low < previous day low (the
      variant definition; "this is what separates it from a New York Reversal").
  b — the Short's own shape reading ("drop during London 2 to 5 to create the wick"): no PD-array
      requirement.
claim '+' in both: beats a matched random entry.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C

RR = 2.0
LONDON = ("02:00", "05:00")
NYAM = ("08:30", "12:00")
MIN_LONDON_M1 = 90


def detect(m1, need_pd=True):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold"]
    d = C.daily(m1)
    lon = C.window_stats(m1, *LONDON, min_n=MIN_LONDON_M1)
    pre = C.window_stats(m1, "18:00", "05:00")
    # London CISD on 15m
    c15 = C.cisd_table(C.complete_bars(m1, "15min"))
    c15 = c15.assign(td=cl.trading_day(c15["extreme_start"]))
    xm = C.mod(c15["extreme_start"])
    c15 = c15[(xm >= C.hm(LONDON[0])) & (xm < C.hm(LONDON[1])) &
              (c15["t"] <= C.ny_local(c15["td"], C.hm(NYAM[0]), day_offset=1))]
    lo, hi = lon["l"].reindex(c15["td"]).to_numpy(), lon["h"].reindex(c15["td"]).to_numpy()
    okb = (c15["dir"].to_numpy() == 1) & np.isclose(c15["extreme_price"].to_numpy(), lo)
    oks = (c15["dir"].to_numpy() == -1) & np.isclose(c15["extreme_price"].to_numpy(), hi)
    lcisd = c15[okb | oks].groupby(["td", "dir"]).head(1)
    lset = set(zip(lcisd["td"], lcisd["dir"]))
    # NY 5m continuation CISD
    b5 = C.complete_bars(m1, "5min")
    c5 = C.cisd_table(b5)
    if c5.empty or not lset:
        return pd.DataFrame(columns=cols)
    a, e = C.hm(NYAM[0]), C.hm(NYAM[1])
    xm, tm = C.mod(c5["extreme_start"]), C.mod(c5["t"] - pd.Timedelta(minutes=1))
    c5 = c5[(xm >= a) & (xm < e) & (tm >= a) & (tm < e)].copy()
    c5["td"] = cl.trading_day(c5["t"])
    c5 = c5[cl.trading_day(c5["extreme_start"]) == c5["td"]]
    # running day extreme at each 5m confirmation (bars closed by t)
    td5 = cl.trading_day(b5.index)
    run_lo = pd.Series(b5["low"].to_numpy()).groupby(td5).cummin().to_numpy()
    run_hi = pd.Series(b5["high"].to_numpy()).groupby(td5).cummax().to_numpy()
    ctn = pd.DatetimeIndex(b5["close_time"]).as_unit("ns").asi8
    pos = np.searchsorted(ctn, pd.DatetimeIndex(c5["t"]).as_unit("ns").asi8)
    c5["run_lo"], c5["run_hi"] = run_lo[pos], run_hi[pos]
    c5["l_lo"] = lon["l"].reindex(c5["td"]).to_numpy()
    c5["l_hi"] = lon["h"].reindex(c5["td"]).to_numpy()
    c5["p_lo"] = pre["l"].reindex(c5["td"]).to_numpy()
    c5["p_hi"] = pre["h"].reindex(c5["td"]).to_numpy()
    pdl = C.prev_day_levels(d, c5["td"])
    c5["pdh"], c5["pdl"] = pdl["pdh"].to_numpy(), pdl["pdl"].to_numpy()
    c5["lc"] = [(t, k) in lset for t, k in zip(c5["td"], c5["dir"])]
    bull = ((c5["dir"] == 1) & c5["lc"] & np.isclose(c5["l_lo"], c5["p_lo"])
            & (c5["extreme_price"] > c5["l_lo"]) & np.isclose(c5["run_lo"], c5["l_lo"]))
    bear = ((c5["dir"] == -1) & c5["lc"] & np.isclose(c5["l_hi"], c5["p_hi"])
            & (c5["extreme_price"] < c5["l_hi"]) & np.isclose(c5["run_hi"], c5["l_hi"]))
    if need_pd:
        bull &= c5["l_lo"] < c5["pdl"]
        bear &= c5["l_hi"] > c5["pdh"]
    q = c5[(bull | bear).to_numpy()].groupby("td", sort=True).head(1)
    t = pd.DatetimeIndex(q["t"])
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": q["dir"].astype(int).to_numpy(),
                        "stop_px": q["stop"].to_numpy(float), "rr": RR,
                        "max_hold": C.session_end(t) - t})
    return out[out["max_hold"] > pd.Timedelta(0)].reset_index(drop=True)


PARAMS = {"london": "02:00-05:00 NY", "ny_am": "08:30-12:00 NY",
          "london_cisd": "15m phase-3 CISD, extreme == London extreme, confirmed by 08:30",
          "ny_entry": "first 5m phase-3 CISD in NY a.m. same direction, London extreme intact",
          "rr": RR, "exit": "17:00 NY session close", "min_london_m1": MIN_LONDON_M1}
SRC = {"london": "corpus: A_mURVLMD-k 'during London or 2 to 5'; session_window_fit",
       "ny_am": "session_window_fit: daily-profile New York a.m. 08:30-12:00",
       "london_cisd": "method_spec: §2.4 London CISD on 15m/30m; phase3 locked CISD config",
       "ny_entry": "corpus: london-reversal-profile execution 'wait for New York to produce an opposing run into London's order block'; method_spec §2.4 NY CISD 5m",
       "rr": "corpus: london-reversal-profile targets '2R (his default in every worked example)'",
       "exit": "declared-before-run: NY continues for the rest of the day",
       "min_london_m1": "declared-before-run: data-hole floor for the London window"}

if __name__ == "__main__":
    for reading, need_pd in (("a", True), ("b", False)):
        det = (lambda m, _n=need_pd: detect(m, need_pd=_n))
        ev = cl.cache_frame(f"lrev_events_{reading}_v1", det if False else (lambda: det(cl.load_m1())))
        print(reading, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(det, ev, lookback="10D")
        print("probe", probe.get("passed"))
        r = cl.trade_test(ev, max_hold=None)
        print({k: r.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars")})
        params = dict(PARAMS, pd_array=("London extreme beyond previous day low/high" if need_pd
                                        else "none required"))
        src = dict(SRC, pd_array=("corpus: london-reversal-profile variant 'That London run reaches a relevant higher-timeframe PD array'; PDH/PDL as the level"
                                  if need_pd else "corpus: A_mURVLMD-k 'We will drop down during London' (no PD array named)"))
        cl.write_result("london-reversal-profile", reading, r,
                        operationalization={"rules": [
                            "London 02:00-05:00 NY makes the day's extreme so far (18:00-05:00)"
                            + (" and takes the previous day's low/high" if need_pd else ""),
                            "a 15m CISD confirms off that London extreme by 08:30 NY",
                            "entry: first 5m CISD in the same direction inside NY 08:30-12:00 "
                            "with London's extreme still intact; stop at its protected swing; "
                            "2R; flat 17:00 NY"], "params": params},
                        params_source=src, script=__file__, probe=probe)
