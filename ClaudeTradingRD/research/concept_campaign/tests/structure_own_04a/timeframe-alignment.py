"""timeframe-alignment — gate_test, two readings (contested).

Concept: true expansion occurs only when the stacked higher-timeframe candles - daily,
4-hour and hourly - all support the same direction at the same moment; the moment of
alignment is the lowest-timeframe closure through the opposing series (a CISD). A setup
with one timeframe not supporting is "materially harder and less clean".

Baseline book (stated): the phase-3 locked rung-0 15m CISD (series_open, 2/2 swings,
close within 3 bars), decide at the confirming 15m close, enter next M1 open, stop =
protected swing, 2R, 150 min (10 entry bars). 15m is the YAML's ltf and the entry TF the
spec pairs with a 4H structure / daily bias stack.

State of each HTF candle at the decision = the IN-PROGRESS candle (built from M1 bars
closed by the decision; at an exact HTF boundary, the just-completed candle), because
he watches the three running candles side by side:
  reading a (wick geometry supports expansion - the per-timeframe rule the corpus gives):
      for each of 1D, 4H, 1H: price beyond the candle open in the trade direction AND the
      opposing run (open -> extreme against) <= |price - open| (small wick <= body,
      threshold_fits grade-A crossover 1.0). aligned = all three.
  reading b ("all timeframes green" - directional agreement only): for each of 1D, 4H,
      1H, price is beyond that candle's open in the trade direction. aligned = all three.
claim '+': aligned CISDs beat non-aligned ones, control-adjusted.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (cl, np, pd, complete_bars, cisd_frame, empty, ns, M1, LiveCandle,  # noqa: E402
                     live_support, PHASE3_SRC, GRID_SRC)

CID = "timeframe-alignment"
LTF = "15min"
GRID = "forex"
RR = 2.0
HOLD = "150min"
STACK = ("1D", "4h", "1h")
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "align_a", "align_b"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, LTF)
    b = complete_bars(b, m1)
    if len(b) < 10:
        return empty(COLS)
    ev = cisd_frame(b)
    if ev.empty:
        return empty(COLS)
    m = M1(m1)
    tdec = ns(ev["conf_close_time"])
    d = ev["sgn"].to_numpy()
    a = np.ones(len(ev), bool)
    g = np.ones(len(ev), bool)
    for tf in STACK:
        st = LiveCandle(m1, m, tf, GRID).at(tdec)
        a &= live_support(st, d, "wick")
        g &= live_support(st, d, "green")
    t = pd.DatetimeIndex(ev["conf_close_time"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d.astype(int),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": RR,
                        "align_a": a, "align_b": g})
    return out[COLS]


RULES = [
    "baseline: 15m CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming bar close, enter next M1 open, "
    "stop = protected swing, 2R, 150 min",
    "HTF state = the in-progress 1D (18:00 NY roll), 4H (forex grid) and 1H candle from M1 bars closed by the decision "
    "(at an exact boundary: the just-completed candle)",
]
GATE = {"a": "gate align_a: on each of 1D/4H/1H price is beyond the candle open in the trade direction AND "
              "opposing run (open -> extreme against) <= |price - open|",
        "b": "gate align_b: on each of 1D/4H/1H price is beyond the candle open in the trade direction ('all green')"}
PARAMS = {"ltf": LTF, "stack": list(STACK), "grid4h": GRID, "level_rule": "series_open", "swing": "2/2",
          "max_wait": 3, "rr": RR, "max_hold": HOLD, "wick_body_cut": 1.0, "boundary_rule": "just-completed candle"}
SRC = {"ltf": "corpus: timeframe-alignment.yaml timeframes ltf [15m, 5m]; method_spec §1.3 favourite stack 1D/4H/15m",
       "stack": "corpus: 'daily, 4-hour and hourly together' (timeframe-alignment.yaml definition)",
       "grid4h": GRID_SRC,
       "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC, "rr": PHASE3_SRC,
       "max_hold": PHASE3_SRC,
       "wick_body_cut": "threshold_fits: small wick = opposing_run/body <= 1.0 (grade A)",
       "boundary_rule": "declared-before-run: at an HTF boundary the new candle has no bars yet; use the candle whose last minute closed"}


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_15m_cisd", lambda: detect(cl.load_m1()))
    print(len(ev), ev["align_a"].mean(), ev["align_b"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"])
    for rd in ("a", "b"):
        col = f"align_{rd}"
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD)
        print(rd, {k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                           "mde", "exposure_bars", "ties", "ctrl_overlap")})
        params = dict(PARAMS)
        if rd == "b":
            params.pop("wick_body_cut")
        src = {k: v for k, v in SRC.items() if k in params}
        p = cl.write_result(CID, rd, res, operationalization={"rules": RULES + [GATE[rd]], "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes=f"gate firing rate {ev[col].mean():.3f}. Weekly/monthly not required ('a day trader "
                                  "does not need the monthly').")
        print(p)
