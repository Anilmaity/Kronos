"""ttfm-hourly-5m-playbook — the published TTFM playbook, in order:
 1 daily bias from the daily closure (no bias -> stop)
 2 hourly CISD confirming that daily candle-2/3 closure (inside the daily candle)
 3 POI: an hourly C2 whose sweep lies in the lower half (bull) / upper half (bear)
   of the previous day's range
 4 hourly candle closure at that POI (sweep the previous hourly extreme, close back inside)
 5 5-minute CISD in the bias direction after that hourly C2
 6 enter; stop on the protected swing; 2R minimum.
One trade_test on the full conjunction vs a matched random entry.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.bias import daily_closures, hourly_cisd_in_candle

CID = "ttfm-hourly-5m-playbook"
RR, HOLD, WAIT5 = 2.0, "50min", pd.Timedelta("60min")


def _bias_days(m1):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= 600].copy()
    cl_ = daily_closures(d[["open", "high", "low", "close"]], c3_reference="c2_open")
    h = cl.build_bars(m1, "1h")[["open", "high", "low", "close"]]
    bias = []
    for t, r in d.iterrows():
        cdir = cl_.loc[t, "closure"]
        if cdir == "none":
            bias.append(0); continue
        end = pd.Timestamp(r["close_time"]) - pd.Timedelta(hours=1)
        ev = hourly_cisd_in_candle(h, t, end, cdir, scope="range", level_rule="series_open")
        bias.append((1 if cdir == "bullish" else -1) if ev is not None else 0)
    d["bias"] = bias
    d["eq"] = (d["high"] + d["low"]) / 2
    return d


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    d = _bias_days(m1)
    h = cl.build_bars(m1, "1h")
    h = h[["open", "high", "low", "close", "close_time"]].copy()
    ph, pl = h["high"].shift(1), h["low"].shift(1)
    bull = ((h["low"] < pl) & (h["close"] > pl)).to_numpy()
    bear = ((h["high"] > ph) & (h["close"] < ph)).to_numpy()
    h["c2"] = np.where(bull & ~bear, 1, np.where(bear & ~bull, -1, 0))
    h = h[h["c2"].isin([1, -1])]
    ct = pd.DatetimeIndex(h["close_time"])
    y = cl.asof(d, ct)                                   # last completed day = yesterday
    same = cl.trading_day(pd.DatetimeIndex(h.index)) > pd.DatetimeIndex(y["trading_day"])
    bias = np.nan_to_num(y["bias"].to_numpy(dtype=float))
    c2 = h["c2"].to_numpy()
    poi = np.where(c2 == 1, h["low"].to_numpy() <= y["eq"].to_numpy(),
                   h["high"].to_numpy() >= y["eq"].to_numpy())
    keep = (bias == c2) & poi & np.asarray(same)
    hc2 = h[keep]
    if hc2.empty:
        return pd.DataFrame(columns=cols)
    b5 = cl.build_bars(m1, "5min")
    ev = cisd_events(b5[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    ev["close"] = pd.DatetimeIndex(b5.loc[ev["confirm_time"], "close_time"])
    ev["dir"] = np.where(ev["direction"] == "bullish", 1, -1)
    ev = ev.sort_values("close")
    ecl = pd.DatetimeIndex(ev["close"]).as_unit("ns").asi8
    rows = []
    for t, r in hc2.iterrows():
        c2close = pd.Timestamp(r["close_time"])
        a = np.searchsorted(ecl, pd.DatetimeIndex([c2close]).as_unit("ns").asi8[0], "right")
        z = np.searchsorted(ecl, pd.DatetimeIndex([c2close + WAIT5]).as_unit("ns").asi8[0], "right")
        cand = ev.iloc[a:z]
        dirn = int(r["c2"])
        cand = cand[(cand["dir"] == dirn) &
                    ((cand["protected_swing"] >= r["low"]) if dirn == 1
                     else (cand["protected_swing"] <= r["high"]))]
        # the hourly C2 must not have been invalidated before the 5m CISD: C2 extreme intact
        if cand.empty:
            continue
        e = cand.iloc[0]
        rows.append({"decision_time": e["close"], "available_at": e["close"],
                     "direction": dirn, "stop_px": float(e["protected_swing"]), "rr": RR})
    out = pd.DataFrame(rows, columns=cols)
    out = out.drop_duplicates("decision_time").sort_values("decision_time").reset_index(drop=True)
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True)
    out["available_at"] = pd.to_datetime(out["available_at"], utc=True)
    return out


def main():
    ev = cl.cache_frame("ttfm_pb_v1", lambda: detect(cl.load_m1()))
    print(len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="12D")
    res = cl.trade_test(ev, max_hold=HOLD, claim="+")
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties", "ctrl_overlap")})
    op = {"rules": [
        "daily bars roll 18:00 NY, stub sessions (<600 M1) skipped",
        "step 1-2: yesterday's daily candle is a C2 closure (detectors.fractal.c2_events: sweep prior extreme, close back inside, close in direction) or a C3 closure (reading A: prior candle took the extreme without a C2, close beyond its open) AND an hourly CISD (series_open) in the same direction inside that daily candle -> today's bias; else no trade",
        "step 3-4: today's hourly C2 in the bias direction (bull: low < prior hour low, close > prior hour low; two-sided excluded) whose sweep extreme lies in the bias-side half of the previous day's range (bull: low <= previous-day EQ)",
        "step 5: the first 5m CISD (series_open, 2/2 swing, max_wait 3) in the bias direction whose confirming bar closes within 60 min after the hourly C2 closes, with its protected swing not beyond the hourly C2 extreme",
        "step 6: enter next M1 open; stop at the 5m protected swing; target 2R; exit after 50 min"],
        "params": {"c3_reference": "c2_open", "cisd_level_rule": "series_open", "poi": "previous-day half (EQ)",
                   "wait_5m": "60min", "rr": RR, "max_hold": HOLD, "cisd5": "2/2 max_wait 3"}}
    src = {"c3_reference": "method_spec: §3.3 reading A (dedicated Shorts)",
           "cisd_level_rule": "method_spec: §4.2 default first-candle-open",
           "poi": "corpus: TNybDCtwBnc playbook step 3 'upper half (bearish) or lower half (bullish) of the previous day's range'",
           "wait_5m": "declared-before-run: the 5m CISD must form in the hourly C3 (the hour after the C2)",
           "rr": "corpus: TNybDCtwBnc 'minimum 2R'",
           "max_hold": "phase3: 10 entry-TF bars (5m stack)",
           "cisd5": "phase3: locked bare-CISD config"}
    print(cl.write_result(CID, None, res, operationalization={"rules": op["rules"], "params": op["params"]},
                          params_source=src, script=__file__, probe=probe,
                          notes="Close relative of phase-3's 5m/1H/1D conjunction (refuted); this is the playbook's own ordering with the previous-day-half POI."))


if __name__ == "__main__":
    main()
