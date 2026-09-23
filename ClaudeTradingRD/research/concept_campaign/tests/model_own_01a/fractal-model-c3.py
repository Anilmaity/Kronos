"""fractal-model-c3 — Candle 3 Continuation / C3 closure (contested).

Claim ('+'): a C3 CLOSURE — used when the reach into the point of interest produced NO
candle-2 closure (candle 2 took the prior candle's extreme but did not close back
inside) and the next candle closes through candle 2 — means "anticipate price to trade
in that direction on the FOLLOWING candle" (C4).

Readings (the concept's own [P], method_spec §3.3 — "compute both"):
  a  Reading A: C3 closes beyond candle 2's OPENING PRICE ("the opening price in candle 2")
  b  Reading B: C3 closes beyond candle 2's EXTREME (high for bullish / low for bearish)
Both from detectors.bias.daily_closures (C3 exists only when the previous candle took
the prior extreme without a C2 closure), applied on 4H candles (forex grid) — the
timeframe the concept lists first after the daily and the one with the sample to decide.

Trade: decide at the C3 close, enter next M1 open in the closure direction; stop beyond
the swing the sequence formed (the lower of C2's and C3's lows for a bullish closure —
execution.stop 'the protected swing'); target 2R (spec §5.3 floor, phase3 locked);
time exit at C4's close (one 4H candle of trading bars).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import cl, np, pd, OHLC, daily_closures  # noqa: E402

READ = sys.argv[1] if len(sys.argv) > 1 else "a"
REF = {"a": "c2_open", "b": "c2_extreme"}[READ]
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def detect(m1):
    b = cl.build_bars(m1, "4h", grid4h="forex")
    b = b[b["n_m1"] >= 60]
    cls = daily_closures(b[OHLC], c3_reference=REF)
    c3 = cls["c3_closure"].to_numpy()
    sel = np.flatnonzero(c3 != "none")
    sel = sel[sel > 0]
    if len(sel) == 0:
        return pd.DataFrame(columns=COLS)
    cur, prev = b.iloc[sel], b.iloc[sel - 1]
    bull = c3[sel] == "bullish"
    stop = np.where(bull, np.minimum(cur["low"].to_numpy(), prev["low"].to_numpy()),
                    np.maximum(cur["high"].to_numpy(), prev["high"].to_numpy()))
    ct = pd.DatetimeIndex(cur["close_time"])
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": np.where(bull, 1, -1),
                         "stop_px": stop.astype(float), "rr": 2.0})


ev = cl.cache_frame(f"c3_{READ}_4h_{REF}", lambda: detect(cl.load_m1()))
print(READ, "events", len(ev), ev["direction"].value_counts().to_dict())
probe = cl.probe_lookahead(detect, ev, lookback="10D")
print("probe", probe.get("passed"))
res = cl.trade_test(ev, max_hold="240min", hold_basis="bars")
for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
          "ties", "exposure_bars", "ctrl_overlap", "halves"):
    print(k, res.get(k))

op = {"rules": [
    "4H bars on the forex grid; bars with < 60 M1 skipped",
    "C3 closure (detectors.bias.daily_closures): previous candle took its prior candle's "
    "low (bullish case) and was NOT a C2 closure; this candle closes above "
    + ("candle 2's OPEN" if READ == "a" else "candle 2's HIGH") + "; mirror bearish",
    "decide at the C3 close_time; enter next M1 open in the closure direction",
    "stop = min(C2 low, C3 low) bullish / max(C2 high, C3 high) bearish; target 2R",
    "time exit after 240 trading M1 bars (C4's duration)"],
    "params": {"tf": "4h", "grid4h": "forex", "min_m1": 60, "c3_reference": REF, "rr": 2.0,
               "max_hold": "240min", "hold_basis": "bars"}}
src = {"tf": "corpus: fractal-model-c3 timeframes htf [1D, 4H]; 4H chosen for sample (declared-before-run)",
       "grid4h": "session_window_fit: forex grid for gold (phase3 knob, primary)",
       "min_m1": "declared-before-run: stub-bar guard (quarter of a full bar)",
       "c3_reference": "method_spec: §3.3 [P] Reading A (C2 opening price) vs Reading B (C2 extreme) — compute both",
       "rr": "phase3: locked 2R fixed target (method_spec §5.3 floor)",
       "max_hold": "corpus: fractal-model-c3 'anticipate price to trade in that direction on the FOLLOWING candle'",
       "hold_basis": "declared-before-run: README trap 7 — 4H holds cross halts"}
p = cl.write_result("fractal-model-c3", READ, res, operationalization=op, params_source=src,
                    script=__file__, probe=probe,
                    notes="The C3-as-a-trade sense (candle after a confirmed C2) is the C2 test "
                          "(fractal-model-c2); this tests the contested C3 CLOSURE sense. No LTF "
                          "CISD required (the Shorts defining the closure do not state it).")
print(p)
