"""v-shape-reversal-speed (TTrades own voice, contested) — batch structure_own_02a.

Claim: a real reversal/continuation trigger is a FAST V-shape — the closure back
through the series of opposing candles should take "1, 2, maybe three" candles
(PQiRV0JMhIQ); longer = consolidation, drop it. Measurable listed in the yaml:
"win rate of continuations bucketed by recovery candle count (1-3 vs 4+)".

Baseline book (both readings): 15m CISD closures (series-open level, method_spec §4.2)
at a POI (the extreme is a 20-bar low/high = the short-term range liquidity taken),
closure within 10 candles of the extreme, no new extreme before it. Decide at the
closing candle's close, enter next M1 open in the closure direction, stop at the
extreme (protected swing), 2R target, 150-min time exit (phase-3 15m convention).
Gate:
  reading a (absolute speed): k = candles from the extreme to the closing candle <= 3
  reading b (relative speed): k <= approach length (the opposing series' candle count)
            — "two candles down met with six candles up" rejected; "two up, two down"
            accepted.
claim '+': fast closures beat slow ones (control-adjusted).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
from _common import cl, cisd_speed, np, pd, summary  # noqa: E402

CID = "v-shape-reversal-speed"
TF, POI_LB, MAX_K, FAST_K, RR, HOLD = "15min", 20, 10, 3, 2.0, "150min"


def detect(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_speed(b, poi_lookback=POI_LB, max_k=MAX_K)
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[ev["j"].to_numpy()])
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": ev["dir"].to_numpy().astype(int),
                         "stop_px": ev["extreme"].to_numpy(), "rr": RR,
                         "k": ev["k"].to_numpy(), "approach": ev["approach"].to_numpy(),
                         "fast_abs": (ev["k"] <= FAST_K).to_numpy(),
                         "fast_rel": (ev["k"] <= ev["approach"]).to_numpy()})


def main():
    ev = cl.cache_frame(f"vshape_speed_{TF}_{POI_LB}_{MAX_K}", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    rules = [f"{TF} bars; extreme = bar whose low (high) is below (above) the 2 prior bars AND "
             f"the lowest low (highest high) of the prior {POI_LB} bars (POI: short-term range "
             "liquidity taken)",
             "opposing series = contiguous down-close (up-close) candles ending at the extreme "
             "(or <=2 bars before it), <=10 long; level = OPEN of its first candle",
             f"closure = first close beyond the level within {MAX_K} candles after the extreme, "
             "no new extreme before it; decide at that close, enter next M1 open",
             f"stop = the extreme (protected swing), target {RR}R, exit after {HOLD}"]
    params = {"tf": TF, "poi_lookback": POI_LB, "left": 2, "max_k": MAX_K, "rr": RR,
              "max_hold": HOLD, "level": "series first-candle open"}
    src = {"tf": "corpus yaml timeframes ltf 15m (PQiRV0JMhIQ counts candles on the chart in use)",
           "poi_lookback": "phase3: lookback 20 knob (backtest_conjunction)",
           "left": "phase3: fractal 2/2 swing knob",
           "max_k": "declared-before-run: closures up to 10 candles form the slow arm (the "
                    "rejected example is 6 candles)",
           "rr": "phase3: 2R target convention", "max_hold": "phase3: 15m book 150-min exit",
           "level": "method_spec: §4.2 first-candle-open default"}
    for reading, col, rule, xp, xs in (
            ("a", "fast_abs", f"gate: k (candles from extreme to closing candle) <= {FAST_K}",
             {"fast_k": FAST_K},
             {"fast_k": "corpus: PQiRV0JMhIQ 'It only takes a couple candles. Now, I prefer 1 2 maybe three.'"}),
            ("b", "fast_rel", "gate: k <= approach (length of the opposing series into the extreme)",
             {"relative": "k <= approach"},
             {"relative": "corpus: PQiRV0JMhIQ 'candles down and we have six candles up and we can't even get back'"})):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res, operationalization={"rules": rules + [rule],
                            "params": {**params, **xp}}, params_source={**src, **xs},
                            script=__file__, probe=probe,
                            notes="gate verdict known at the closing candle's close (k and the "
                                  "approach length are both fixed then). Control-adjusted R per "
                                  "trade, so the tighter stops of fast closures are matched.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
