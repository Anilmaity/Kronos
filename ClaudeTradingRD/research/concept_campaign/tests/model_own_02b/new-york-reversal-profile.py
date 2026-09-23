"""new-york-reversal-profile (model, TTrades own voice, contested).

Reading (trade_test): London runs counter to the day's eventual direction but does NOT reach
the relevant HTF level; New York a.m. reaches it, changes the state of delivery there, and
expands away.
  * relevant HTF level = previous day low (bullish) / high (bearish) — the corpus's own example
    ("previous day low as sellside liquidity"); prior complete (non-stub) session.
  * London (02:00-05:00 NY) ran counter: London low < midnight open (bullish case) — and
    London FAILED to reach the level: London low > PDL.
  * New York a.m. (08:30-12:00 NY): a 5m CISD (phase-3 config) in the bullish direction whose
    extreme formed inside the window and traded below PDL (the level reached), confirmed inside
    the window. Bearish mirror. First qualifying event of the day only (one CISD per day).
  * Enter at the next M1 open after the confirming 5m close; stop at the protected swing;
    target 2R ("over two R" floor); flat at the 17:00 NY session close ("expands for the rest
    of the day").
claim '+': beats a matched random entry (same direction/stop/target/hold).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C

TF = "5min"
RR = 2.0
LONDON = ("02:00", "05:00")
NYAM = ("08:30", "12:00")
MIN_LONDON_M1 = 90


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold"]
    d = C.daily(m1)
    lon = C.window_stats(m1, *LONDON, min_n=MIN_LONDON_M1)
    mid = C.window_stats(m1, "00:00", "00:05")
    b = C.complete_bars(m1, TF)
    cz = C.cisd_table(b)
    if cz.empty:
        return pd.DataFrame(columns=cols)
    a, e = C.hm(NYAM[0]), C.hm(NYAM[1])
    xm, tm = C.mod(cz["extreme_start"]), C.mod(cz["t"] - pd.Timedelta(minutes=1))
    cz = cz[(xm >= a) & (xm < e) & (tm >= a) & (tm < e)].copy()
    cz["td"] = cl.trading_day(cz["t"])
    cz = cz[cl.trading_day(cz["extreme_start"]) == cz["td"]]
    pdl = C.prev_day_levels(d, cz["td"])
    cz["pdh"], cz["pdl"] = pdl["pdh"].to_numpy(), pdl["pdl"].to_numpy()
    cz["l_lo"] = lon["l"].reindex(cz["td"]).to_numpy()
    cz["l_hi"] = lon["h"].reindex(cz["td"]).to_numpy()
    cz["mo"] = mid["o"].reindex(cz["td"]).to_numpy()
    bull = ((cz["dir"] == 1) & (cz["l_lo"] > cz["pdl"]) & (cz["l_lo"] < cz["mo"])
            & (cz["extreme_price"] < cz["pdl"]))
    bear = ((cz["dir"] == -1) & (cz["l_hi"] < cz["pdh"]) & (cz["l_hi"] > cz["mo"])
            & (cz["extreme_price"] > cz["pdh"]))
    q = cz[(bull | bear).to_numpy()]
    q = q.groupby("td", sort=True).head(1)
    t = pd.DatetimeIndex(q["t"])
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": q["dir"].astype(int).to_numpy(),
                        "stop_px": q["stop"].to_numpy(float), "rr": RR,
                        "max_hold": C.session_end(t) - t})
    return out[out["max_hold"] > pd.Timedelta(0)].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("nyrev_events_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    r = cl.trade_test(ev, max_hold=None)
    print({k: r.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars")})
    params = {"tf": TF, "cisd": "series_open, swing 2/2, max_wait 3", "rr": RR,
              "london": "02:00-05:00 NY", "ny_am": "08:30-12:00 NY",
              "htf_level": "previous day high/low (prior non-stub session)",
              "london_counter": "London low < midnight open (bullish) / high > midnight open",
              "exit": "17:00 NY session close", "min_london_m1": MIN_LONDON_M1,
              "one_per_day": True}
    src = {"tf": "method_spec: §2.4 New York CISD timeframe 5m or 15m",
           "cisd": "phase3: locked CISD config",
           "rr": "corpus: RZsgWeMBWGI/xdzyejskSKE stop chosen for 'over two R'; method_spec §5.3",
           "london": "session_window_fit: daily-profile London 02:00-05:00",
           "ny_am": "session_window_fit: daily-profile New York a.m. 08:30-12:00",
           "htf_level": "corpus: new-york-reversal-profile precondition 'previous day low as sellside liquidity'",
           "london_counter": "declared-before-run: 'London ran counter to the intended direction' as trading through the midnight open (anchor stated in qFtfD09Vv3E)",
           "exit": "corpus: xdzyejskSKE 'expands for the rest of the day'",
           "min_london_m1": "declared-before-run: data-hole floor for the London window",
           "one_per_day": "method_spec: §2.4 only one CISD per day"}
    cl.write_result("new-york-reversal-profile", None, r,
                    operationalization={"rules": [
                        "PDH/PDL of the prior complete session as the relevant HTF level",
                        "London 02:00-05:00 NY ran counter through the midnight open but did not "
                        "reach PDL (bullish) / PDH (bearish)",
                        "a 5m CISD in NY 08:30-12:00 whose extreme (inside the window) took PDL "
                        "(bullish) / PDH (bearish); first per day",
                        "enter at next M1 open, stop at protected swing, 2R, flat at 17:00 NY"],
                        "params": params},
                    params_source=src, script=__file__, probe=probe,
                    notes="'Relevant' PD array is undefined in the corpus; PDH/PDL is its own "
                          "worked example. Not modelled: the failed-first-CISD re-anchoring (the "
                          "first confirmed CISD beyond the level is taken).")
