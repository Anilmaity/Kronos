"""four-candle-model-window — (batch model_own_04a). Contested; two readings.

reading a (gate_test) — the four-candle window as a HARD window: the model is framed
  on four higher-timeframe candles (C1 liquidity, C2 swing/reversal, C3 and C4 the
  continuation) and "fewer than four is not supported"; the open question the
  concept names is whether a setup that needs a fifth candle is dead. Test: in the
  TTFM playbook pairing (hourly structure, 5-minute entry), take every 5m CISD in the
  direction of the most recent 1H C2 closure that fires during the next four hourly
  candles. Gate = the entry fires inside the four-candle window (during C3 or C4);
  complement = it fires in C5 or C6. claim '+': inside-window entries are better.
reading b — UNTESTABLE: the numbering/labelling convention itself.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.fractal import c2_events

MAX_HOLD = "50min"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, "5min")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "c2_close", "candle_no", "in_window"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})
    h = cl.build_bars(m1, "1h")
    c2 = c2_events(h[["open", "high", "low", "close"]], sweep_ref="prior_candle",
                   require_close_inside=True, require_reversal_close=True)
    if c2.empty:
        return pd.DataFrame(columns=cols)
    hpos = h.index.get_indexer(pd.DatetimeIndex(c2["time"]))
    c2_ct = pd.DatetimeIndex(h["close_time"].to_numpy()[hpos]).as_unit("ns")
    order = np.argsort(c2_ct.asi8, kind="stable")
    c2_ct, hpos = c2_ct[order], hpos[order]
    c2_dir = np.where(c2["direction"].to_numpy()[order] == "bullish", 1, -1)
    dt = pd.DatetimeIndex(out["decision_time"]).as_unit("ns")
    k = np.searchsorted(c2_ct.asi8, dt.asi8, side="right") - 1
    ok = k >= 0
    out, k, dt = out[ok].copy(), k[ok], dt[ok]
    # hourly candle that contains the deciding 5m bar (its last minute is decision-1ns)
    hstart = pd.DatetimeIndex(h.index).as_unit("ns").asi8
    cur = np.searchsorted(hstart, (dt - pd.Timedelta(1, "ns")).asi8, side="right") - 1
    offset = cur - hpos[k]                       # 1 = C3, 2 = C4, 3 = C5, 4 = C6
    keep = (offset >= 1) & (offset <= 4) & (out["direction"].to_numpy() == c2_dir[k])
    out = out[keep].copy()
    out["c2_close"] = pd.DatetimeIndex(c2_ct[k[keep]])
    out["candle_no"] = (offset[keep] + 2).astype(int)
    out["in_window"] = out["candle_no"].to_numpy() <= 4
    return out.reset_index(drop=True)


REASON_B = ("The labelling convention itself (C2 = the swing candle, C1 before it, C3 and C4 after; "
            "count from 0 or 1; the indicator's default of four HTF candles; the C1 sweep marker "
            "shown or hidden) is a naming and display definition. It asserts nothing about price "
            "that could come out true or false: every swing point can be numbered this way by "
            "construction. The behavioural content (C2/C3 closures, C4 continuation, the hard "
            "four-candle window) is tested in reading a and in the fractal-model-c2/c3/c4 concepts.")


def run_a():
    ev = cl.cache_frame("fourcandle_5m_cisd_1hc2", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "in_window", mask_available_at="decision_time", max_hold=MAX_HOLD)
    op = {"rules": [
        "structure: 1H C2 closure (sweep of the prior hourly candle's extreme, close back "
        "inside, reversal close) = candle 2; the next hourly candles are C3, C4, C5, C6",
        "entries: bare 5m CISD (series_open, 2/2, max_wait 3) in the C2's direction, using the "
        "most recent 1H C2, deciding inside C3..C6; enter next M1 open, stop at the protected "
        "swing, 2R, 50 min hold",
        "gate: entry decided inside the four-candle window (C3 or C4); complement: C5 or C6"],
        "params": {"htf": "1h", "entry_tf": "5min", "window_candles": 4,
                   "complement_candles": "C5-C6", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "rr": 2.0, "max_hold": MAX_HOLD}}
    src = {"htf": "method_spec: §1.3 TTFM playbook (hourly structure, 5-minute CISD)",
           "entry_tf": "method_spec: §1.2 pairing 1-hour -> 5-minute",
           "window_candles": "corpus: sdZkE-naNiY 'my model just needs four candles'",
           "complement_candles": ("declared-before-run: two candles past the window, matching "
                                  "the two in-window continuation candles; method_spec §3.4 'from "
                                  "C5 onward, treat a new phase of price as likely'"),
           "level_rule": "phase3: locked CISD config", "swing": "phase3: locked CISD config",
           "max_wait": "phase3: locked CISD config", "rr": "method_spec: §5.3 2R",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    notes = ("A pure clock-position gate relative to an already-closed C2, so mask_available_at = "
             "decision_time. No POI or SMT gate is applied (phase 3 found none load-bearing).")
    p = cl.write_result("four-candle-model-window", "a", res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "n_complement", "gate_firing_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print("  ", k, res.get(k))


if __name__ == "__main__":
    what = sys.argv[1:] or ["a", "b"]
    if "a" in what:
        run_a()
    if "b" in what:
        print(cl.write_untestable("four-candle-model-window", REASON_B, reading="b",
                                  script=__file__))
