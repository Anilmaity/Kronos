"""new-york-manipulation-profile (model, TTrades own voice, contested).

London (02:00-05:00 NY) consolidates / fails to reach an HTF PD array, leaving a London range.
New York (at 08:30 or 09:30) sweeps one side of that range (the manipulation), changes the state
of delivery, and expands the other way; stop beyond the manipulation extreme; target the
previous day high (bullish) / low (bearish).

Operationalisation (bullish; bearish mirrors):
  * London failed to reach the HTF PD array: London high < previous day high AND London low >
    previous day low (London stayed inside the prior session's range).
  * NY manipulation: a 5m CISD (phase-3 config) bullish whose extreme formed in 08:30-10:00 NY
    (the 8:30 / 9:30 candidates) and swept the London low (extreme < London low), confirmed
    by 12:00 NY. First qualifying event of the day only.
  * enter next M1 open after the confirming close; stop at the protected swing (the
    manipulation extreme); target = previous day high (the stated target); events where the
    target is not beyond the entry-decision close are dropped; flat 17:00 NY.
Single reading — the variants agree on the mechanics; they differ only on which range is
manipulated (London's range is the one named in every variant).
claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C

LONDON = ("02:00", "05:00")
MANIP = ("08:30", "10:00")
NYAM_END = "12:00"
MIN_LONDON_M1 = 90


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    d = C.daily(m1)
    lon = C.window_stats(m1, *LONDON, min_n=MIN_LONDON_M1)
    c5 = C.cisd_table(C.complete_bars(m1, "5min"))
    if c5.empty:
        return pd.DataFrame(columns=cols)
    a, e, z = C.hm(MANIP[0]), C.hm(MANIP[1]), C.hm(NYAM_END)
    xm, tm = C.mod(c5["extreme_start"]), C.mod(c5["t"] - pd.Timedelta(minutes=1))
    c5 = c5[(xm >= a) & (xm < e) & (tm >= a) & (tm < z)].copy()
    c5["td"] = cl.trading_day(c5["t"])
    c5 = c5[cl.trading_day(c5["extreme_start"]) == c5["td"]]
    pdl = C.prev_day_levels(d, c5["td"])
    c5["pdh"], c5["pdl"] = pdl["pdh"].to_numpy(), pdl["pdl"].to_numpy()
    c5["l_lo"] = lon["l"].reindex(c5["td"]).to_numpy()
    c5["l_hi"] = lon["h"].reindex(c5["td"]).to_numpy()
    inside = (c5["l_hi"] < c5["pdh"]) & (c5["l_lo"] > c5["pdl"])
    bull = inside & (c5["dir"] == 1) & (c5["extreme_price"] < c5["l_lo"]) & (c5["pdh"] > c5["confirm_close"])
    bear = inside & (c5["dir"] == -1) & (c5["extreme_price"] > c5["l_hi"]) & (c5["pdl"] < c5["confirm_close"])
    q = c5[(bull | bear).to_numpy()].groupby("td", sort=True).head(1)
    t = pd.DatetimeIndex(q["t"])
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": q["dir"].astype(int).to_numpy(),
                        "stop_px": q["stop"].to_numpy(float),
                        "target_px": np.where(q["dir"] == 1, q["pdh"], q["pdl"]).astype(float),
                        "max_hold": C.session_end(t) - t})
    return out[out["max_hold"] > pd.Timedelta(0)].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("nymanip_events_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    r = cl.trade_test(ev, max_hold=None)
    print({k: r.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars")})
    params = {"london": "02:00-05:00 NY", "manipulation_window": "extreme in 08:30-10:00 NY",
              "confirm_by": "12:00 NY", "cisd": "5m, series_open, swing 2/2, max_wait 3",
              "london_failed": "London range inside the previous session's range",
              "target": "previous day high/low", "exit": "17:00 NY session close",
              "min_london_m1": MIN_LONDON_M1, "one_per_day": True}
    src = {"london": "session_window_fit: daily-profile London 02:00-05:00",
           "manipulation_window": "corpus: 4629-YQ7_9g 'either 8:30 or 9:30' (window closes before the 10:00 candle)",
           "confirm_by": "session_window_fit: New York a.m. 08:30-12:00",
           "cisd": "phase3: locked CISD config; method_spec §2.4 NY CISD on 5m",
           "london_failed": "corpus: IeXtmeKqjnQ 'London is consolidating or failing to reach a higher time frame key level' (PDH/PDL as the key level)",
           "target": "corpus: 4629-YQ7_9g 'stop on the low, targeting the previous day high'",
           "exit": "corpus: new-york-manipulation-profile 'expands the other way for the rest of the day'",
           "min_london_m1": "declared-before-run: data-hole floor for the London window",
           "one_per_day": "method_spec: §2.4 only one CISD per day"}
    cl.write_result("new-york-manipulation-profile", None, r,
                    operationalization={"rules": [
                        "London 02:00-05:00 NY stays inside the previous day's range (failed to "
                        "reach PDH/PDL)",
                        "a 5m CISD whose extreme formed 08:30-10:00 NY beyond London's low "
                        "(bullish) / high (bearish), confirmed by 12:00; first per day",
                        "enter next M1 open; stop at the protected swing; target PDH (long) / "
                        "PDL (short), dropped if already passed; flat 17:00 NY"],
                        "params": params},
                    params_source=src, script=__file__, probe=probe)
