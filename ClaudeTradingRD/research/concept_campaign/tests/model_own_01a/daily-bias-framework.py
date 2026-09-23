"""daily-bias-framework — Previous Candle High / Low Bias (TTrades own voice, contested).

Claim ('+'): the previous-candle engine (spec §2.3) picks which of the just-closed
candle's extremes the NEXT candle reaches: continuation closure -> same side, reversal
closure (took a side, closed back inside) -> opposite side, both sides -> no bias,
inside bar -> default to trend, range-bound -> none.

Test: trade_test. At the close of candle D, enter in the implied bias, target = D's
bias-side extreme (the draw, execution.targets 'the previous higher-timeframe candle's
high/low'), stop = D's opposite extreme (the level whose loss means the side-choice
was wrong), time exit after one candle of the same timeframe (the bias is for the NEXT
candle). A matched random entry with the same direction/stop/target distances is the
null, so this asks: does the engine choose the side better than chance given geometry?

Readings (contested: which timeframe the engine runs on):
  a  daily candles (18:00 NY roll) -> next session.     definition[0], detection 9-10
  b  4-hour candles (forex grid 17/21/01/05/09/13 NY) -> next 4H candle.
     definition: 'He runs this candle-by-candle on the 4-hour'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import *   # noqa: F401,F403
from _common import cl, daily, engine_bias, next_candle_draw_events, MIN_DAY_M1

READ = sys.argv[1] if len(sys.argv) > 1 else "a"


def detect_a(m1):
    return next_candle_draw_events(engine_bias(daily(m1)))


def detect_b(m1):
    b = cl.build_bars(m1, "4h", grid4h="forex")
    b = b[b["n_m1"] >= 60]
    return next_candle_draw_events(engine_bias(b))


if READ == "a":
    detect, key, hold, lb = detect_a, "dbf_a_1D_engine", "1380min", "20D"
else:
    detect, key, hold, lb = detect_b, "dbf_b_4h_engine", "240min", "10D"

ev = cl.cache_frame(key, lambda: detect(cl.load_m1()))
print(READ, "events", len(ev), ev["direction"].value_counts().to_dict())
probe = cl.probe_lookahead(detect, ev, lookback=lb)
print("probe", probe.get("passed"))
res = cl.trade_test(ev, max_hold=hold, hold_basis="bars")
for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
          "ties", "exposure_bars", "ctrl_overlap", "halves"):
    print(k, res.get(k))

tf = "1D (18:00 NY roll)" if READ == "a" else "4h forex grid"
op = {"rules": [
    f"candles: {tf}; bias-source candle skipped if it has fewer than the stub-filter M1 bars",
    "previous-candle engine (detectors.bias.previous_candle_state): took one side and closed "
    "outside -> same direction; took one side and closed back inside -> opposite; both sides "
    "-> no bias; inside bar -> last resolved side (trend); 3 inside bars -> none",
    "decide at the biased candle's close_time; enter next M1 open in the bias direction",
    "target = that candle's bias-side extreme (high if bullish), stop = its opposite extreme",
    f"time exit after {hold} of trading bars (one candle of the same timeframe)"],
    "params": {"timeframe": tf, "stub_filter_min_m1": MIN_DAY_M1 if READ == "a" else 60,
               "range_lookback": 3, "max_hold": hold, "hold_basis": "bars",
               "grid4h": "forex"}}
src = {"timeframe": ("corpus: daily-bias-framework definition 'read off a single daily closure' (a) / "
                     "'He runs this candle-by-candle on the 4-hour' (b)"),
       "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions; example_rate uses n_m1>600 (1D); 60 M1 for 4H",
       "range_lookback": "method_spec: §2.3 range-bound state, detectors.bias default 3",
       "max_hold": "declared-before-run: the bias is for the NEXT candle only (one candle of trading bars)",
       "hold_basis": "declared-before-run: README trap 7 — daily/4H exits cross the 17:00 halt and weekends",
       "grid4h": "session_window_fit: forex grid for gold (carried as knob per phase3)"}
p = cl.write_result("daily-bias-framework", READ, res, operationalization=op, params_source=src,
                    script=__file__, probe=probe,
                    notes="Stop/target are the biased candle's own extremes; the matched control "
                          "shares direction and both distances, so geometry cancels. "
                          + ("" if READ != "a" else "RE-RUN NOTE (reading a): the first locked run used ctrl_tod_tol_min=30; "
                          "because the book fires at the same 18:00 NY reopen almost every day, "
                          "45% of control draws were the concept's own trades (ctrl_overlap), "
                          "making the verdict UNDERPOWERED by construction (diff -0.018 "
                          "[-0.074,+0.025]). Treated as an operationalisation bug (a time-of-day "
                          "match on a once-per-day fixed-clock event), fixed by dropping the "
                          "time-of-day match, re-run once. Both runs are in the ledger."))
print(p)
