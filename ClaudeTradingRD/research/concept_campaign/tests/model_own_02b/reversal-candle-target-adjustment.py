"""reversal-candle-target-adjustment (model, TTrades own voice, contested).

When the daily candle in play is a reversal candle (large opposing run), expansion past its
open is not expected: trade it on the lower timeframe back toward the daily OPEN (reading a),
or — the variant — toward the current day's opposing extreme inside the day's range (reading b).

Shared entries (bullish; bearish mirrors), 1h execution:
  * the day opened and traded DOWN first, taking the previous day's low (the extreme formed
    from a key level), and price is still below the daily open (large opposing run in play);
  * a 1h CISD (phase-3 config) bullish, extreme inside today and equal to today's low so far,
    confirmed today with its close below the daily 18:00 open; first per day;
  * enter next M1 open; stop at the protected swing (the day's low); flat at 17:00 NY.
Targets:
  a — the daily opening price (the candle's own open).
  b — the current day's opposing extreme so far (today's high at the decision), i.e. the
      session extreme inside the day's range.
claim '+': beats the matched random entry with the same stop/target distances.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C


def reversal_day_entries(m1):
    """Tier-3 / reversal-candle entries with both candidate targets."""
    d = C.daily(m1)
    dayo = C.window_stats(m1, "18:00", "17:00")          # whole session; 'o' = 18:00 open
    h = C.complete_bars(m1, "1h")
    cz = C.cisd_table(h)
    cols = ["t", "dir", "stop", "open_px", "opp_px", "td"]
    if cz.empty:
        return pd.DataFrame(columns=cols)
    td_h = cl.trading_day(h.index)
    run_lo = pd.Series(h["low"].to_numpy()).groupby(td_h).cummin().to_numpy()
    run_hi = pd.Series(h["high"].to_numpy()).groupby(td_h).cummax().to_numpy()
    ctn = pd.DatetimeIndex(h["close_time"]).as_unit("ns").asi8
    pos = np.searchsorted(ctn, pd.DatetimeIndex(cz["t"]).as_unit("ns").asi8)
    cz = cz.assign(td=cl.trading_day(cz["t"]), run_lo=run_lo[pos], run_hi=run_hi[pos])
    cz = cz[cl.trading_day(cz["extreme_start"]) == cz["td"]]
    pdl = C.prev_day_levels(d, cz["td"])
    cz["pdh"], cz["pdl"] = pdl["pdh"].to_numpy(), pdl["pdl"].to_numpy()
    cz["dopen"] = dayo["o"].reindex(cz["td"]).to_numpy()
    bull = ((cz["dir"] == 1) & np.isclose(cz["extreme_price"], cz["run_lo"])
            & (cz["run_lo"] < cz["pdl"]) & (cz["confirm_close"] < cz["dopen"]))
    bear = ((cz["dir"] == -1) & np.isclose(cz["extreme_price"], cz["run_hi"])
            & (cz["run_hi"] > cz["pdh"]) & (cz["confirm_close"] > cz["dopen"]))
    q = cz[(bull | bear).to_numpy()].groupby("td", sort=True).head(1)
    return pd.DataFrame({"t": pd.DatetimeIndex(q["t"]), "dir": q["dir"].astype(int).to_numpy(),
                         "stop": q["stop"].to_numpy(float), "open_px": q["dopen"].to_numpy(float),
                         "opp_px": np.where(q["dir"] == 1, q["run_hi"], q["run_lo"]).astype(float),
                         "td": q["td"].to_numpy()})


def detect(m1, target="open"):
    q = reversal_day_entries(m1)
    t = pd.DatetimeIndex(q["t"])
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": q["dir"].to_numpy(), "stop_px": q["stop"].to_numpy(),
                        "target_px": (q["open_px"] if target == "open" else q["opp_px"]).to_numpy(),
                        "max_hold": C.session_end(t) - t})
    return out[out["max_hold"] > pd.Timedelta(0)].reset_index(drop=True)


PARAMS = {"exec_tf": "1h", "cisd": "series_open, swing 2/2, max_wait 3",
          "key_level": "previous day low/high taken by today's extreme",
          "reversal_candle": "price still beyond the daily open at the CISD close (opposing run in play)",
          "daily_open": "18:00 NY", "exit": "17:00 NY session close", "one_per_day": True}
SRC = {"exec_tf": "method_spec: §2.4 daily wick confirmed by an hourly CISD",
       "cisd": "phase3: locked CISD config",
       "key_level": "corpus: reversal-candle-target-adjustment precondition 'The day's extreme formed from a key level' (PDH/PDL)",
       "reversal_candle": "declared-before-run: live proxy for 'large opposing wick' (wick size is only final at the close)",
       "daily_open": "method_spec: §1.4 daily open 18:00 canon",
       "exit": "corpus: SlWxhzhLo3A targets 'inside the current day's range'",
       "one_per_day": "method_spec: §2.4 only one CISD per day"}

if __name__ == "__main__":
    for reading, tgt in (("a", "open"), ("b", "opposing_extreme")):
        det = (lambda m, _t=tgt: detect(m, target=_t))
        ev = cl.cache_frame(f"rcta_events_{reading}_v1", lambda: det(cl.load_m1()))
        print(reading, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(det, ev, lookback="20D")
        print("probe", probe.get("passed"))
        r = cl.trade_test(ev, max_hold=None)
        print({k: r.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars")})
        params = dict(PARAMS, target=("daily 18:00 open" if tgt == "open"
                                      else "today's opposing extreme at the decision"))
        src = dict(SRC, target=("corpus: SlWxhzhLo3A 'return back to its opening price'" if tgt == "open"
                                else "corpus: reversal-candle-target-adjustment variant 'typically the current day's opposing extreme, which will be a session high or low'"))
        cl.write_result("reversal-candle-target-adjustment", reading, r,
                        operationalization={"rules": [
                            "the day trades below the previous day low (bullish case) and a 1h "
                            "CISD confirms off the day's low so far while price is still below "
                            "the 18:00 daily open; first per day (bearish mirror)",
                            "enter next M1 open; stop at the protected swing; target = "
                            + ("the daily open" if tgt == "open" else
                               "today's high so far (low for shorts)") + "; flat 17:00 NY"],
                            "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Failure-swing / low-resistance escalation and the FVG-near-open "
                              "refinement are discretionary and not modelled.")
