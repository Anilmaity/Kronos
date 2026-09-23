"""autobias-filter — gate_test (batch model_own_04a).

Concept: Autobias aligns the model traded on a chart with the fractal model one
(autobias 1) or two (autobias 2) timeframes up and suppresses every setup that
opposes it. Worked example: on a 5-minute chart, autobias 1 = the 4-hour model,
autobias 2 = the daily model (bearish daily -> no bullish setup all day).

Baseline book (stated): the bare 5-minute CISD (phase-3 rung-0 detector: close
through the opening price of the opposing series after a 2/2 swing, within 3 bars),
both directions, stop at the protected swing, 2R, max hold 10 entry bars (50 min).

Gate: the event's direction == the direction of the governing higher-timeframe
fractal model, defined (declared before run, the corpus does not say how it is
computed) as the direction of the most recent completed C2 closure on that HTF
(detectors.fractal.c2_events: sweep of the prior candle's extreme, close back
inside, close in the reversal direction), read strictly as-of its close_time and
held until an opposite C2 prints.
  reading a = autobias 1: 4H (forex grid) governs the 5m chart
  reading b = autobias 2: 1D (18:00 NY roll) governs the 5m chart
claim '+': gated (agreeing) setups beat suppressed (opposing) setups.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.fractal import c2_events

HTF = {"a": "4h", "b": "1D"}
MAX_HOLD = "50min"


def detect(m1: pd.DataFrame, htf: str) -> pd.DataFrame:
    b = cl.build_bars(m1, "5min")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "htf_dir", "htf_avail", "agree"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})
    h = cl.build_bars(m1, htf)
    c2 = c2_events(h[["open", "high", "low", "close"]], sweep_ref="prior_candle",
                   require_close_inside=True, require_reversal_close=True)
    if c2.empty:
        return pd.DataFrame(columns=cols)
    c2_ct = pd.DatetimeIndex(h.loc[c2["time"], "close_time"]).as_unit("ns")
    c2_dir = np.where(c2["direction"] == "bullish", 1, -1)
    order = np.argsort(c2_ct.asi8, kind="stable")
    c2_ct, c2_dir = c2_ct[order], c2_dir[order]
    k = np.searchsorted(c2_ct.asi8, pd.DatetimeIndex(out["decision_time"]).as_unit("ns").asi8,
                        side="right") - 1
    ok = k >= 0
    out = out[ok].copy()
    k = k[ok]
    out["htf_dir"] = c2_dir[k]
    out["htf_avail"] = c2_ct[k]
    out["agree"] = (out["direction"].to_numpy() == out["htf_dir"].to_numpy())
    return out.reset_index(drop=True)


def run(reading: str):
    htf = HTF[reading]
    fn = lambda m: detect(m, htf)
    ev = cl.cache_frame(f"autobias_5m_cisd_htf{htf}", lambda: fn(cl.load_m1()))
    probe = cl.probe_lookahead(fn, ev, lookback="20D" if htf == "4h" else "45D")
    res = cl.gate_test(ev, "agree", mask_available_at="htf_avail", max_hold=MAX_HOLD)
    op = {"rules": [
        "baseline: bare 5m CISD, series_open level, 2/2 swing, max_wait 3, min_series 1; "
        "decide at the confirming 5m bar's close, enter next M1 open, stop at the protected "
        "swing, 2R target, 50 min max hold",
        f"HTF direction: most recent completed C2 closure on {htf} (sweep prior candle's "
        "extreme, close back inside, reversal close), as-of its close_time, held until an "
        "opposite C2",
        "gate: setup direction == HTF direction (autobias on); complement = setups the "
        "filter suppresses; events before the first HTF C2 dropped"],
        "params": {"entry_tf": "5min", "htf": htf, "grid4h": "forex", "day_open_hour": 18,
                   "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                   "min_series": 1, "rr": 2.0, "max_hold": MAX_HOLD,
                   "htf_direction_rule": "last C2 closure"}}
    src = {"entry_tf": "corpus: sdZkE-naNiY worked example on a 5-minute chart",
           "htf": ("corpus: sdZkE-naNiY 'Autobias means it's aligning a higher time frame with "
                   "a lower time frame'; AB1 = 4H, AB2 = daily per the concept's worked example"),
           "grid4h": "session_window_fit: forex grid for gold",
           "day_open_hour": "method_spec: §1.4 daily open 18:00 (canon)",
           "level_rule": "phase3: locked CISD config (series_open)",
           "swing": "phase3: locked CISD config (2/2)",
           "max_wait": "phase3: locked CISD config (max_wait 3)",
           "min_series": "phase3: locked CISD config",
           "rr": "method_spec: §5.3 2R floor/fixed target",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "htf_direction_rule": ("declared-before-run: the corpus does not say how the "
                                  "governing direction is computed; C2 closure is the model's "
                                  "reversal print (method_spec §3.2)")}
    notes = ("HTF bars built from the same M1 input; the C2 is read only after its close_time. "
             f"Firing rate of the gate is in the result. Reading {reading}.")
    p = cl.write_result("autobias-filter", reading, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print(reading, p)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print("  ", k, res.get(k))
    print("   gate", {k: res.get(k) for k in ("gate", "firing_rate", "arms") if k in res})
    return res


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        run(r)
