"""automatic-fractal-pairing (specified, own voice, sdZkE-naNiY): the indicator's automatic map
from chart TF to the HTF candle the fractal model is read on -- 1H chart -> daily, 15m -> 4H,
5m -> 1H.

The concept is a mapping; the only outcome it implies ('performance by fractal pair') is that a
chart-TF setup read against its auto-paired HTF candle carries information. Test (declared
before any run): pool the phase-3 bare CISD books of the three auto rungs (1h hold 10h, 15m hold
150min, 5m hold 50min -- max_hold per row). For each event read the auto-paired HTF bar that
last COMPLETED before the decision (cl.asof; 4H on the forex grid, 1D rolling 18:00 NY) and ask
whether it is a candle 2 in the event's direction: bullish C2 = low below the prior HTF bar's
low and close back inside the prior bar's range; bearish mirror. gated = the event's direction
matches a C2 on its auto-paired HTF; complement = no matching C2. Gate test, claim '+'.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, summarize, PH3

PAIRS = {"1h": "1D", "15min": "4h", "5min": "1h"}
HOLDS = {"1h": "10h", "15min": "150min", "5min": "50min"}


def c2_frame(m1, htf):
    b = cl.build_bars(m1, htf)
    pl, ph = b["low"].shift(1), b["high"].shift(1)
    bull = (b["low"] < pl) & (b["close"] > pl) & (b["close"] < ph)
    bear = (b["high"] > ph) & (b["close"] < ph) & (b["close"] > pl)
    c2 = np.where(bull, 1, np.where(bear, -1, 0)).astype(float)
    return pd.DataFrame({"close_time": b["close_time"].to_numpy(), "c2": c2}, index=b.index)


def detect(m1):
    parts = []
    for tf, htf in PAIRS.items():
        e = cisd_book(m1, tf)
        t = pd.DatetimeIndex(e["decision_time"]).tz_convert("UTC")
        a = cl.asof(c2_frame(m1, htf), t)
        c2 = a["c2"].to_numpy(float)
        ok = np.isfinite(c2)
        e["gated"] = c2 == e["direction"].to_numpy()
        e["mask_at"] = pd.DatetimeIndex(a["available_at"]).tz_convert("UTC")
        e["tf"] = tf
        e["max_hold"] = pd.Timedelta(HOLDS[tf])
        parts.append(e[ok])
    ev = pd.concat(parts, ignore_index=True).sort_values(["decision_time", "tf"], kind="stable").reset_index(drop=True)
    ev["mask_at"] = pd.DatetimeIndex(ev["mask_at"])
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("to02b_autofractal_3rungs", lambda: detect(cl.load_m1()))
    print(len(ev), "events"); print(pd.crosstab(ev["tf"], ev["gated"]))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, "gated", mask_available_at="mask_at", claim="+")
    summarize(res)
    params = {"baseline": "bare CISD", "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": 2.0,
              "rungs": "1h->1D, 15m->4H, 5m->1H (pooled)", "max_hold": "10 entry-TF periods per row",
              "grid4h": "forex", "day_open": "18:00 NY",
              "c2_rule": "HTF bar sweeps the prior HTF bar's low (high) and closes back inside its range"}
    src = {k: PH3 for k in ("baseline", "level_rule", "swing", "max_wait", "rr", "max_hold")}
    src.update({"rungs": "corpus: sdZkE-naNiY 'if I'm right here on the hourly, it's going to use the daily' (auto map 1H/1D, 15m/4H, 5m/1H)",
                "grid4h": "session_window_fit: forex grid for gold (carried as a knob per phase 3)",
                "day_open": "session_window_fit: 18:00 NY daily anchor",
                "c2_rule": "method_spec: candle 2 = sweep of the prior candle's extreme closing back inside (fractal model)"})
    rules = ["baseline: phase-3 bare CISD on 1h, 15m, 5m pooled; entry next M1 open, protected-swing stop, 2R, hold 10 entry-TF periods",
             "for each event, the auto-paired HTF bar last completed before the decision (1h->1D, 15m->4H, 5m->1H)",
             "gated = that HTF bar is a candle 2 in the event's direction; complement = otherwise"]
    p = cl.write_result("automatic-fractal-pairing", None, res,
                        operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="The mapping itself is indicator configuration; this scores its only implied outcome (auto-paired HTF candle-2 context adds information to the chart-TF setup). The 17-bar offset is a display convenience and not modelled.")
    print(p)
