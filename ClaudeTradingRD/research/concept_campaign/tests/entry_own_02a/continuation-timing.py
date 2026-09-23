"""continuation-timing -- continuations must form early in a new HTF candle, and fast.

Gate tests (the concept is a timing filter on an existing entry). Two distinct
readings in the YAML variants, declared before any run:

  a  WHERE IN THE HTF CANDLE (PQiRV0JMhIQ / SlWxhzhLo3A / Vo2n47RjjMo): frame the
     entry early in a new higher-timeframe candle, reject late ones.
     Baseline: 5m CISD (series_open, 2/2, max_wait 3) taken only in the direction
     of the previous completed 1H candle (the HTF candle "whose direction supports
     the trade"), stop = protected swing, 2R, 50 min hold.
     Gate: the decision (5m close) falls in the first 15 min of the current 1H
     candle (a close at :00 is minute 0 of the NEW candle = "wait for the next open").
     15 min = time_share 0.25 (threshold_fits time-axis default); it also satisfies
     the worked rejection "40 minutes left in an hourly candle".
  b  SPEED (7v9Y2GHNqCg / ZEK8fDzxClA / v-shape speed): a continuation must close
     through in a couple of candles; 3 candles struggling then the 4th = consolidation.
     Baseline: 15m CISD with max_wait 10 (so slow closures exist), stop = protected
     swing, 2R, 150 min. Gate: confirm bar - extreme bar <= 3 bars.
claim '+': gated beats complement on control-adjusted R.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CID = "continuation-timing"
EARLY_MIN = 15
FAST_BARS = 3


def detect_a(m1):
    b = cl.build_bars(m1, "5min")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "early"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    dt = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    d = np.where(ev["direction"] == "bullish", 1, -1)
    h1 = cl.prior_hilo(dt, "1h", m1=m1)             # last COMPLETED 1H candle at dt
    hd = np.sign(h1["close"].to_numpy(float) - h1["open"].to_numpy(float))
    keep = np.nan_to_num(hd, nan=0) == d
    elapsed = dt.minute.to_numpy()                   # minutes since the 1H open
    out = pd.DataFrame({"decision_time": dt, "available_at": dt, "direction": d,
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                        "early": elapsed <= EARLY_MIN})
    return out[keep].reset_index(drop=True)[cols]


def detect_b(m1):
    b = cl.build_bars(m1, "15min")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=10)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "fast"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    pos = pd.Series(np.arange(len(b)), index=b.index)
    nb = pos.loc[ev["confirm_time"]].to_numpy() - pos.loc[ev["extreme_time"]].to_numpy()
    dt = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({"decision_time": dt, "available_at": dt,
                         "direction": np.where(ev["direction"] == "bullish", 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                         "fast": nb <= FAST_BARS})[cols]


if __name__ == "__main__":
    specs = {
        "a": dict(det=detect_a, col="early", hold="50min",
                  rules=["baseline: 5m CISD (series_open, 2/2, max_wait 3) in the direction of "
                         "the previous completed 1H candle (close vs open); decide at the 5m "
                         "close, next-M1-open entry, stop = protected swing, 2R, 50 min",
                         "gate: decision within the first 15 min of the current 1H candle "
                         "(minute-of-hour <= 15; :00 = start of the new candle)"],
                  params={"exec_tf": "5min", "htf": "1h", "early_minutes": EARLY_MIN,
                          "max_wait": 3, "rr": 2.0, "max_hold": "50min",
                          "htf_direction_filter": "prior 1H close vs open"},
                  src={"exec_tf": "phase3: 5m/1H/1D stack (pre-designated powered cell)",
                       "htf": "phase3: 5m/1H/1D stack; YAML htf includes 1H",
                       "early_minutes": "threshold_fits: time-axis default time_share 0.25 "
                                        "(=15 of 60 min); corpus SlWxhzhLo3A '40 minutes "
                                        "left' rejection",
                       "max_wait": "phase3: locked max_wait=3",
                       "rr": "phase3: locked 2R", "max_hold": "phase3: 10 entry-TF bars",
                       "htf_direction_filter": "corpus: YAML precondition 'A higher-timeframe "
                                               "candle whose direction supports the intended "
                                               "trade'; declared-before-run: prior 1H close vs open"}),
        "b": dict(det=detect_b, col="fast", hold="150min",
                  rules=["baseline: 15m CISD (series_open, 2/2, max_wait 10), decide at the "
                         "confirming close, stop = protected swing, 2R, 150 min",
                         "gate: close-through arrives <= 3 bars after the extreme bar "
                         "(fast V); 4+ = consolidation per the Short"],
                  params={"exec_tf": "15min", "max_wait": 10, "fast_bars": FAST_BARS,
                          "rr": 2.0, "max_hold": "150min"},
                  src={"exec_tf": "phase3: 15m entry TF",
                       "max_wait": "declared-before-run: 10 bars so that slow (consolidation) "
                                   "closures exist in the baseline to be gated out",
                       "fast_bars": "method_spec: 4.2 speed 'I prefer 1, 2, maybe three'; "
                                    "corpus 7v9Y2GHNqCg 'It takes 1 2 3 candles and we're "
                                    "struggling to close below this level'",
                       "rr": "phase3: locked 2R", "max_hold": "phase3: 10 entry-TF bars"}),
    }
    for reading, s in specs.items():
        ev = cl.cache_frame(f"{CID}_{reading}_v1", lambda d=s["det"]: d(cl.load_m1()))
        print(reading, len(ev), ev[s["col"]].mean())
        probe = cl.probe_lookahead(s["det"], ev, lookback="20D")
        res = cl.gate_test(ev, s["col"], mask_available_at="decision_time",
                           max_hold=s["hold"])
        print(reading, {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p",
                                                  "verdict", "verdict_detail", "ties")})
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": s["rules"] + [
                                "claim '+': gated beats complement on control-adjusted R"],
                                "params": s["params"]},
                            params_source=s["src"], script=__file__, probe=probe,
                            notes="Two distinct readings of the timing doctrine: (a) position "
                                  "in the HTF candle, (b) closure speed. 'Early' is never "
                                  "quantified in the corpus; 0.25 of the candle is the "
                                  "threshold_fits default.")
        print("wrote", p)
