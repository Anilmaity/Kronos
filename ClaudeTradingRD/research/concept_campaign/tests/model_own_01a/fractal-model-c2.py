"""fractal-model-c2 — Candle 2 Closure (the reversal candle) (contested).

Claim ('+'): a valid C2 — the candle takes the previous candle's high (low), closes back
below (above) it, at a point of interest, confirmed by a change in the state of delivery
inside C2 on the aligned lower timeframe — sets up candle 3 in the reversal direction.

Operationalisation (spec §3.2 + §3.5, detection rules):
  * C2: detectors.fractal.c2_events defaults — sweep of the PRIOR candle's extreme,
    close back inside it, close in the reversal direction ("the candle's own shape must
    be a reversal", approximated by the close direction as the detector documents).
  * Gate 1 (POI): "a high/low being taken out" — C2 by construction takes out candle 1's
    extreme, so the gate is satisfied by the sweep itself.
  * Gate 2 (LTF CISD inside C2, same direction): detectors.bias.hourly_cisd_in_candle on
    the paired lower timeframe, series_open level, scope 'range'.
  * Trade C3: decide at C2's close, enter next M1 open in the reversal direction; stop
    beyond the C2 extreme (execution.stop); target = the nearest unswept previous-candle
    extreme on the far side, "starting with candle 1's" (execution.targets) — for a
    bullish C2 the higher of C1's high and C2's high; time exit at C3's close (one HTF
    candle of trading bars; spec §5.5 time-based exit at the HTF candle close).

Readings (contested across timeframes; the model is fractal and names these pairings):
  a  4H C2 (forex grid) confirmed by a 15m CISD   — favourite stack, spec §1.3
  b  1H C2 confirmed by a 5m CISD                 — playbook stack, spec §1.3
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import cl, np, pd, OHLC, c2_events, ltf_cisd_inside  # noqa: E402

READ = sys.argv[1] if len(sys.argv) > 1 else "a"
CFG = {"a": dict(htf="4h", ltf="15min", min_m1=60, hold="240min", lb="10D"),
       "b": dict(htf="1h", ltf="5min", min_m1=20, hold="60min", lb="5D")}[READ]
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def detect(m1):
    b = cl.build_bars(m1, CFG["htf"], grid4h="forex")
    b = b[b["n_m1"] >= CFG["min_m1"]]
    lt = cl.build_bars(m1, CFG["ltf"])
    c2 = c2_events(b[OHLC])
    if c2.empty:
        return pd.DataFrame(columns=COLS)
    pos = b.index.get_indexer(pd.DatetimeIndex(c2["time"]))
    rows = b.iloc[pos].copy()
    rows["direction"] = c2["direction"].to_numpy()
    conf = ltf_cisd_inside(b, lt, rows)
    prev = b.iloc[np.maximum(pos - 1, 0)]
    bull = (rows["direction"] == "bullish").to_numpy()
    tgt = np.where(bull, np.maximum(prev["high"].to_numpy(), rows["high"].to_numpy()),
                   np.minimum(prev["low"].to_numpy(), rows["low"].to_numpy()))
    ct = pd.DatetimeIndex(rows["close_time"])
    out = pd.DataFrame({"decision_time": ct, "available_at": ct,
                        "direction": np.where(bull, 1, -1),
                        "stop_px": np.where(bull, rows["low"], rows["high"]).astype(float),
                        "target_px": tgt.astype(float)})
    return out[conf & (pos > 0)].reset_index(drop=True)


ev = cl.cache_frame(f"c2_{READ}_{CFG['htf']}_{CFG['ltf']}", lambda: detect(cl.load_m1()))
print(READ, "events", len(ev), ev["direction"].value_counts().to_dict())
probe = cl.probe_lookahead(detect, ev, lookback=CFG["lb"])
print("probe", probe.get("passed"))
res = cl.trade_test(ev, max_hold=CFG["hold"], hold_basis="bars")
for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
          "ties", "exposure_bars", "ctrl_overlap", "halves"):
    print(k, res.get(k))

op = {"rules": [
    f"HTF bars {CFG['htf']} (4h on the forex grid); bars with < {CFG['min_m1']} M1 skipped",
    "C2: low < prior low and close >= prior low and close > open (bullish); mirror bearish "
    "(detectors.fractal.c2_events defaults)",
    "POI: satisfied by the sweep of candle 1's extreme",
    f"confirmation: a {CFG['ltf']} CISD inside C2 in the same direction (series_open, scope range)",
    "decide at C2 close_time; enter next M1 open; stop = C2 extreme; target = max(C1 high, C2 "
    "high) bullish / min(C1 low, C2 low) bearish",
    f"time exit after {CFG['hold']} of trading bars (C3's duration)"],
    "params": {"htf": CFG["htf"], "ltf": CFG["ltf"], "grid4h": "forex", "min_m1": CFG["min_m1"],
               "sweep_ref": "prior_candle", "require_reversal_close": True,
               "cisd_level": "series_open", "cisd_scope": "range",
               "target": "nearest unswept of C1/C2 far extremes", "max_hold": CFG["hold"],
               "hold_basis": "bars"}}
src = {"htf": "method_spec: §1.3 named stacks (favourite 4H/15m; playbook 1H/5m)",
       "ltf": "method_spec: §1.2 timeframe pairing table (4-hour->15-minute, 1-hour->5-minute)",
       "grid4h": "session_window_fit: forex grid for gold (phase3 knob, primary)",
       "min_m1": "declared-before-run: stub-bar guard (quarter of a full bar)",
       "sweep_ref": "corpus: fractal-model-c2 'take out its PREVIOUS CANDLE'S high'",
       "require_reversal_close": "corpus: fractal-model-c2 'The candle's own shape must be a reversal'",
       "cisd_level": "phase3: locked CISD level rule (first-candle open)",
       "cisd_scope": "phase3: locked primary cisd_scope=range",
       "target": "corpus: fractal-model-c2 execution.targets 'previous candles' unswept highs/lows' / method_spec §5.2 'starting with candle 1's'",
       "max_hold": "method_spec: §5.5 time-based exit at the close of the HTF candle traded (C3)",
       "hold_basis": "declared-before-run: README trap 7 — 4H/1H holds cross halts"}
p = cl.write_result("fractal-model-c2", READ, res, operationalization=op, params_source=src,
                    script=__file__, probe=probe,
                    notes="Wick-size tradeability and 'ideal formation' refinements not applied; "
                          "the two gates the spec calls required (POI, LTF CISD) are.")
print(p)
