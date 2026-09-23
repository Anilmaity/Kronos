"""no-fading-the-daily-candle (TTrades own voice, contested) — batch model_own_01b.

Filter: do not take intraday trades against the CURRENT (developing) daily candle.
Baseline book: the phase-3 bare 15m CISD (series_open, swing 2/2, max_wait 3, stop
at the protected swing, 2R, 10 entry bars) — the timeframes block lists 15m/5m as
the LTF this filter is applied to.

Reading a: the developing daily candle's direction = sign(last M1 close - 18:00
           daily open) at the decision time. Gate = trade direction agrees.
Reading b: the 'supported direction' reading — the developing candle must also show
           a small wick on the open side: opposing run (open -> extreme against the
           direction) <= 1.0 x its body so far (threshold_fits grade-A cut). Gate =
           trade direction agrees with a candle that supports expansion that way.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import PHASE3, cisd_book, cl, developing_day, np, pd, summary  # noqa: E402

CID = "no-fading-the-daily-candle"
WICK_CUT = 1.0


def detect(m1):
    ev = cisd_book(m1, "15min")
    dd = developing_day(m1, ev["decision_time"])
    o, h, l, c = (dd[k].to_numpy() for k in ("d_open", "d_high", "d_low", "d_close"))
    sgn = np.sign(c - o)
    dirn = ev["direction"].to_numpy()
    aligned = (sgn == dirn) & ~np.isnan(sgn)
    body = np.abs(c - o)
    opp = np.where(dirn > 0, o - l, h - o)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(body > 0, opp / body, np.inf)
    ev = ev.drop(columns=["extreme_time", "extreme_price"])
    ev["gate_a"] = aligned
    ev["gate_b"] = aligned & (ratio <= WICK_CUT)
    return ev


def main():
    ev = cl.cache_frame("nofade_cisd15_v1", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    base_rules = ["baseline: 15m bare CISD (series_open, swing 2/2, max_wait 3), decide at "
                  "the confirming bar close, enter next M1 open, stop protected swing, 2R, 150 min",
                  "developing daily candle = 18:00 NY trading day: first M1 open, running "
                  "high/low and last M1 close from bars closed by the decision time"]
    base_params = {"baseline_tf": "15min", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "rr": 2.0, "max_hold": "150min", "day_open_hour": 18}
    base_src = {"baseline_tf": "corpus: no-fading-the-daily-candle.yaml timeframes ltf ['15m','5m']",
                "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
                "max_hold": "phase3: 10 entry-TF bars (§1.13)",
                "day_open_hour": "method_spec: §1.4 daily open 18:00 canon"}
    for reading, col, extra, xp, xs in (
            ("a", "gate_a", ["gate: trade direction == sign(last close - daily open) of the "
                             "developing daily candle (doji -> not aligned)"], {}, {}),
            ("b", "gate_b", ["gate: trade direction == developing candle direction AND its "
                             "opposing run (open->extreme against the trade) <= 1.0 x body"],
             {"wick_cut_body": WICK_CUT},
             {"wick_cut_body": "threshold_fits: small wick opposing_run/body <= 1.0 (grade A)"})):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold="150min")
        print(f"reading {reading}\n" + summary(res))
        op = {"rules": base_rules + extra, "params": {**base_params, **xp}}
        p = cl.write_result(CID, reading, res, operationalization=op,
                            params_source={**base_src, **xs}, script=__file__, probe=probe,
                            notes="gate verdict uses only M1 bars closed by the decision "
                                  "(developing candle), so mask_available_at = decision_time.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
