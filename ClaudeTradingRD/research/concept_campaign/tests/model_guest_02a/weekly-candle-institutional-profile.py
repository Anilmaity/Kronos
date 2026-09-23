"""weekly-candle-institutional-profile (guest: Gene, nncJGt6j19Q).

Claim: institutions accumulate below the weekly opening price (midnight NY) in a
bullish week and distribute above it in a bearish one, so the trader should "buy at or
below the opening price if I'm bullish" (sell at or above it if bearish).

Operationalisation (gate_test, claim '+'): the actionable rule is a LOCATION gate on
entries relative to the weekly open. The weekly draw (the unit's direction source) is
deferred to an absent part two, so the trade direction comes from a neutral, locked
baseline book: bare 1h CISD in the phase-3 locked configuration (series_open level,
2/2 swings, max_wait 3, stop at the protected swing, 2R, 10h hold).
  gate = long whose confirming close is <= the week's Monday 00:00 NY open, or short
         whose confirming close is >= it.
  Only events after that week's weekly open is printed are in the book (Sunday-evening
  events before Monday midnight have no weekly open yet and are dropped).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events


def weekly_midnight_open(m1):
    loc = m1.index.tz_convert("America/New_York")
    sel = (loc.dayofweek == 0) & (loc.hour == 0) & (loc.minute < 5)
    sub = m1[sel]
    key = sub.index.tz_convert("America/New_York").normalize().tz_localize(None)
    g = pd.DataFrame({"px": sub["open"].to_numpy(), "t": sub.index}, index=key)
    return g.groupby(level=0).first()          # index: Monday date (naive)


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "weekly_open", "at_or_beyond_open"]
    b = cl.build_bars(m1, "1h")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"]).tz_convert("UTC")
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                        "cclose": ev["confirm_close"].to_numpy(float)})
    sdate = cl.session_date(out["decision_time"])
    monday = (sdate - pd.to_timedelta(sdate.dayofweek, unit="D")).normalize()
    wo = weekly_midnight_open(m1)
    px = wo["px"].reindex(monday).to_numpy(float)
    t_open = pd.DatetimeIndex(wo["t"].reindex(monday))
    ok = ~np.isnan(px) & ~pd.isna(t_open)
    ok[ok] = (t_open[ok] + pd.Timedelta(minutes=1)) <= out["decision_time"].to_numpy()[ok]
    out = out[ok].copy()
    out["weekly_open"] = px[ok]
    out["at_or_beyond_open"] = np.where(out["direction"] == 1,
                                        out["cclose"] <= out["weekly_open"],
                                        out["cclose"] >= out["weekly_open"]).astype(bool)
    return out[cols].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("wcip_cisd1h_wopen_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["at_or_beyond_open"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "at_or_beyond_open", mask_available_at="decision_time",
                       max_hold="10h")
    for k in ("n", "n_gated", "gate_rate", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "ties", "ctrl_overlap", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "baseline: bare 1h CISD, phase-3 locked config (series_open, 2/2 swing, "
        "max_wait 3), decide at the confirming bar close, stop protected swing, 2R, 10h",
        "weekly open = first M1 open 00:00-00:05 NY on Monday; events before it in the "
        "week are dropped",
        "gate: long with confirming close <= weekly open, or short with close >= it"],
        "params": {"baseline_tf": "1h", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "rr": 2.0, "max_hold": "10h",
                   "weekly_open": "Monday 00:00 NY", "location_price": "confirming close"}}
    ph3 = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked 1h CISD config)"
    src = {k: ph3 for k in ("baseline_tf", "level_rule", "swing", "max_wait", "rr",
                            "max_hold")}
    src["weekly_open"] = ("corpus: nncJGt6j19Q 'weekly opening price is measured at "
                          "00:00 New York, not 00:00 GMT'")
    src["location_price"] = ("corpus: nncJGt6j19Q 'buy at or below the opening price if "
                             "I'm bullish' (declared-before-run: price = the close the "
                             "entry decision is made on)")
    p = cl.write_result("weekly-candle-institutional-profile", None, res,
                        operationalization=op, params_source=src, script=__file__,
                        probe=probe,
                        notes="Direction from a neutral 1h CISD baseline because the "
                              "unit's weekly-draw method is absent; tests only the "
                              "at/below-weekly-open location rule.")
    print(p)
