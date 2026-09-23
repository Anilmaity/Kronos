"""volatility-timeframe-selection (underspecified, own voice, W7Fu3Rx5iMs / X4XSsv5CNqg):
'as volatility goes up you can use smaller time frames' / 'if the volatility is really low, use
a higher time frame'. His live example dropped from the 15m to the 5m because the move would
complete inside one 15m candle.

Test (declared before any run): pool the phase-3 bare CISD books on the two timeframes of his
worked example, 15m (hold 150 min) and 5m (hold 50 min) -- max_hold per row, 10 entry-TF
periods each. At each decision, volatility state = mean range of the last 12 completed 5m bars
divided by the median of that same statistic over the preceding 20 x 276 completed 5m bars
(~20 sessions); HIGH when > 1 (a median split: the corpus gives only the direction of the
relation, never a level). gated = the TF the rule selects: 5m events in HIGH volatility, 15m
events in LOW volatility; complement = the mismatched pairings. Gate test, claim '+'.
This is the interaction the rule asserts: 'R difference between taking the closure one
timeframe up versus down' conditioned on volatility.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params, base_rule, summarize

LOOK = 20 * 276


def vol_state(m1):
    b5 = cl.build_bars(m1, "5min")
    rng = (b5["high"] - b5["low"]).astype(float)
    s12 = rng.rolling(12, min_periods=12).mean()
    ref = s12.shift(1).rolling(LOOK, min_periods=LOOK // 2).median()
    return pd.DataFrame({"close_time": b5["close_time"].to_numpy(),
                         "ratio": (s12 / ref).to_numpy()}, index=b5.index)


def detect(m1):
    parts = []
    for tf in ("5min", "15min"):
        e = cisd_book(m1, tf)
        e["tf"] = tf
        e["max_hold"] = pd.Timedelta({"5min": "50min", "15min": "150min"}[tf])
        parts.append(e)
    ev = pd.concat(parts, ignore_index=True).sort_values(["decision_time", "tf"], kind="stable").reset_index(drop=True)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    v = cl.asof(vol_state(m1), t)
    r = v["ratio"].to_numpy(float)
    ok = np.isfinite(r)
    high = r > 1.0
    ev["gated"] = np.where(ev["tf"].to_numpy() == "5min", high, ~high)
    ev["vol_ratio"] = r
    return ev[ok].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("to02b_voltf_5_15", lambda: detect(cl.load_m1()))
    print(len(ev), "events; gated share", ev["gated"].mean())
    print(pd.crosstab(ev["tf"], ev["vol_ratio"] > 1))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, "gated", mask_available_at="decision_time", claim="+")
    summarize(res)
    bp, bs = base_params("15min")
    bp.pop("max_hold"); bs.pop("max_hold")
    params = {**bp, "baseline_tf": "5min + 15min pooled", "max_hold": "10 entry-TF periods (50min / 150min per row)",
              "vol_measure": "mean 5m bar range over last 12 completed 5m bars / median of same over previous 5,520 5m bars",
              "vol_split": "ratio > 1 = high"}
    src = {**bs, "baseline_tf": "corpus: X4XSsv5CNqg live example dropped 15m -> 5m for volatility",
           "max_hold": "phase3: 10 entry-TF periods (§5.5)",
           "vol_measure": "declared-before-run: volatility is never quantified in the corpus [GAP]; scale-free recent-vs-typical range ratio (trap 6: no raw dollars)",
           "vol_split": "declared-before-run: median split; only the direction of the relation is stated"}
    rules = ["baseline: phase-3 bare CISD books on 5m (hold 50min) and 15m (hold 150min), pooled, next-M1-open entry, protected-swing stop, 2R",
             "volatility state at the decision from completed 5m bars only",
             "gated = 5m events in high volatility + 15m events in low volatility; complement = 5m-low + 15m-high"]
    p = cl.write_result("volatility-timeframe-selection", None, res,
                        operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="The 'sloppy -> step back up' clause is visual and not modelled. Both books share decision times at 15m closes; the day-block CI absorbs that dependence.")
    print(p)
