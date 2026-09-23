"""premium-discount (TTrades own voice, contested) — batch structure_own_02a.

Two readings, both his, and he calls the later one "the opposite" of the first:
  a  EARLIER / ORTHODOX: discount := below the midnight open, premium := above it;
     longs only in discount, shorts only in premium ("line in the sand").
  b  LATER / INVERTED ("You Are Using Discount and Premium Wrong! - EQ For Expansions"):
     the EQ of the previous candle must HOLD for the direction to survive — a long is
     valid only while price is in the upper half of the previous (daily) candle, a short
     only while it is in the lower half; a retracement into the far half kills the read.
Both are filters applied UNDER an existing directional setup, so both are gate tests on
one baseline book: 15m CISD closures at a POI (series-open level, extreme = 20-bar
low/high, closure within 10 candles), decide at the closing candle's close, enter next
M1 open, stop at the extreme, 2R, 150-min exit (phase-3 15m convention).
The location is read from the closing candle's close (the price known at the decision).
Reading a keeps only events at 00:00-17:00 NY (the midnight open of that trading day must
already exist; events before it are dropped, not passed).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
from _common import cl, cisd_speed, np, pd, summary  # noqa: E402

CID = "premium-discount"
TF, POI_LB, MAX_K, RR, HOLD = "15min", 20, 10, 2.0, "150min"


def _base(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_speed(b, poi_lookback=POI_LB, max_k=MAX_K)
    j = ev["j"].to_numpy()
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[j])
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": ev["dir"].to_numpy().astype(int),
                         "stop_px": ev["extreme"].to_numpy(), "rr": RR,
                         "px": b["close"].to_numpy()[j]})


def detect_a(m1):
    ev = _base(m1)
    mo = cl.open_at(ev["decision_time"], "00:00", m1=m1)
    ok = mo["price"].notna().to_numpy() & (cl.ny_minute_of_day(ev["decision_time"]) < 17 * 60)
    ev = ev[ok].copy()
    lvl = mo["price"].to_numpy()[ok]
    ev["midnight_open"] = lvl
    ev["available_at"] = pd.DatetimeIndex(ev["decision_time"])   # the open is earlier still
    ev["in_pd"] = np.where(ev["direction"] > 0, ev["px"] < lvl, ev["px"] > lvl)
    return ev.reset_index(drop=True)


def detect_b(m1):
    ev = _base(m1)
    pd_ = cl.prior_hilo(ev["decision_time"], "1D", m1=m1, min_coverage=0.5)
    ok = pd_["high"].notna().to_numpy()
    ev = ev[ok].copy()
    eq = ((pd_["high"] + pd_["low"]) / 2).to_numpy()[ok]
    ev["pd_eq"] = eq
    ev["eq_holds"] = np.where(ev["direction"] > 0, ev["px"] > eq, ev["px"] < eq)
    return ev.reset_index(drop=True)


def main():
    base_rules = [f"baseline: {TF} CISD closure at a POI — extreme = bar below its 2 prior lows "
                  f"and the lowest low of the prior {POI_LB} bars (mirror for highs); level = "
                  "open of the first candle of the opposing series; first close beyond it "
                  f"within {MAX_K} candles, no new extreme first",
                  f"decide at the closing candle's close, enter next M1 open in the closure "
                  f"direction, stop = the extreme, {RR}R target, exit after {HOLD}",
                  "location = the closing candle's close"]
    base_params = {"tf": TF, "poi_lookback": POI_LB, "max_k": MAX_K, "rr": RR, "max_hold": HOLD}
    base_src = {"tf": "corpus yaml timeframes: 15m listed (htf 1D/1H/15m); phase3 15m stack",
                "poi_lookback": "phase3: lookback 20 knob",
                "max_k": "declared-before-run: closures up to 10 candles after the extreme",
                "rr": "phase3: 2R", "max_hold": "phase3: 15m book 150-min exit"}
    for reading, det, key, col, rule, xp, xs in (
            ("a", detect_a, "pd_a", "in_pd",
             "gate (orthodox): long only below the NY midnight open (discount), short only "
             "above it (premium); events 00:00-17:00 NY only",
             {"anchor": "NY 00:00 open of the trading day (open_at, max_delay 5 min)"},
             {"anchor": "corpus yaml variant (earlier recording): 'discount := below the midnight or 08:30 open; buy there' — midnight chosen"}),
            ("b", detect_b, "pd_b", "eq_holds",
             "gate (inverted): long only while price is ABOVE the previous daily candle's EQ "
             "((PDH+PDL)/2, 18:00 NY day), short only below it",
             {"anchor": "EQ of the previous trading day's high-low (min_coverage 0.5)"},
             {"anchor": "method_spec: §3.7 reading (a) previous-day-range EQ / yaml 'Which range ... in this video it is the previous candle'"})):
        ev = cl.cache_frame(f"premdisc_{key}_{TF}_{POI_LB}_{MAX_K}", lambda d=det: d(cl.load_m1()))
        probe = cl.probe_lookahead(det, ev, lookback="10D")
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res, operationalization={
            "rules": base_rules + [rule], "params": {**base_params, **xp}},
            params_source={**base_src, **xs}, script=__file__, probe=probe,
            notes="The two readings partition the book on different anchors, so they are not "
                  "mirror images. Reading b applies the inversion to every event; the corpus "
                  "restricts it to expansion phases and gives no mechanical phase classifier.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
