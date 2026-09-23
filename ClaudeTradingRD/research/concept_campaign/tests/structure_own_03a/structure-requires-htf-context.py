"""structure-requires-htf-context (TTrades own voice, contested) — batch structure_own_03a.

Doctrine: never read lower-timeframe structure without a higher-timeframe bias; a LTF
structure shift against the HTF is "just a retracement to a higher-timeframe PD array"
and is expected to FAIL.

Baseline book (both readings): phase-3 bare 5m CISD (series_open, swing 2/2,
max_wait 3), decide at the confirming close, enter next M1 open, stop at the protected
swing, 2R, 50 min (10 entry bars). Stack 5m under 1H/1D (yaml timeframes; the worked
example checks a 5m break against the hourly).

Reading a (daily anchor — "Step 1: find a daily candle 2 closure and take its direction.
  Step 2: inside that day, look for structure only in that direction"): keep events whose
  previous completed 18:00-NY daily candle is a C2 or C3 closure (no anchor -> no read);
  gate = the 5m CISD agrees with that closure's direction. claim '+'.
Reading b (HTF PD array — "a 5-minute structure break looked valid, but ... was only a
  retracement into an hourly fair value gap ... that retracement was going to fail"):
  gate = at the decision the 5m CISD's close sits inside an OPPOSING, still-open 1h FVG
  (bullish CISD inside a bearish 1h FVG, and mirror), FVG created within the last 24
  closed 1h bars and not traded through by any closed 1h bar since. claim '-'.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
from _common import PHASE3, cl, np, pd, summary  # noqa: E402
from detectors.bias import daily_closures  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

CID = "structure-requires-htf-context"
TF, HOLD, FVG_LB = "5min", "50min", 24


def _cisd_book(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    t = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({"decision_time": t, "available_at": t,
                         "direction": np.where(ev["direction"] == "bullish", 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                         "px": ev["confirm_close"].to_numpy(float)})


def _daily_dir(m1, t):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] > 0]
    cl_ = daily_closures(d[["open", "high", "low", "close"]])
    dirn = np.select([cl_["closure"] == "bullish", cl_["closure"] == "bearish"], [1, -1], 0)
    ct = cl.data.utc_ns(pd.DatetimeIndex(d["close_time"]))
    k = np.searchsorted(ct, cl.data.utc_ns(t), side="right") - 1
    out = np.zeros(len(t), int)
    ok = k >= 1                      # need the prior day to exist for the C2 test
    out[ok] = dirn[k[ok]]
    return out


def _in_opposing_fvg(m1, t, direction, px):
    h1 = cl.build_bars(m1, "1h")
    h, l = h1["high"].to_numpy(float), h1["low"].to_numpy(float)
    ct = cl.data.utc_ns(pd.DatetimeIndex(h1["close_time"]))
    n = len(h1)
    bear_top = np.full(n, np.nan); bear_bot = np.full(n, np.nan)
    bull_top = np.full(n, np.nan); bull_bot = np.full(n, np.nan)
    if n >= 3:
        bm = h[2:] < l[:-2]              # bearish FVG stamped on the third bar
        bear_top[2:][bm] = l[:-2][bm]; bear_bot[2:][bm] = h[2:][bm]
        um = l[2:] > h[:-2]
        bull_top[2:][um] = l[2:][um]; bull_bot[2:][um] = h[:-2][um]
    tn = cl.data.utc_ns(t)
    last = np.searchsorted(ct, tn, side="right") - 1     # last 1h bar closed by t
    res = np.zeros(len(t), bool)
    for r in range(len(t)):
        k = last[r]
        if k < 2:
            continue
        lo = max(2, k - FVG_LB + 1)
        if direction[r] > 0:            # bullish shift inside a BEARISH 1h FVG
            tops, bots = bear_top[lo:k + 1], bear_bot[lo:k + 1]
            for i in np.flatnonzero(np.isfinite(tops)):
                c = lo + i
                if c < k and h[c + 1:k + 1].max() >= tops[i]:
                    continue            # traded through since creation
                if bots[i] <= px[r] <= tops[i]:
                    res[r] = True
                    break
        else:                           # bearish shift inside a BULLISH 1h FVG
            tops, bots = bull_top[lo:k + 1], bull_bot[lo:k + 1]
            for i in np.flatnonzero(np.isfinite(tops)):
                c = lo + i
                if c < k and l[c + 1:k + 1].min() <= bots[i]:
                    continue
                if bots[i] <= px[r] <= tops[i]:
                    res[r] = True
                    break
    return res


def detect(m1, reading: str):
    ev = _cisd_book(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "gate"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(ev["decision_time"])
    d = ev["direction"].to_numpy()
    if reading == "a":
        dd = _daily_dir(m1, t)
        ev["gate"] = dd == d
        ev = ev[dd != 0]
    else:
        ev["gate"] = _in_opposing_fvg(m1, t, d, ev["px"].to_numpy())
    ev = ev[cols]
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    base = [f"baseline: {TF} bare CISD (series_open, swing 2/2, max_wait 3), decide at the "
            f"confirming bar close, enter next M1 open, stop protected swing, 2R, {HOLD}"]
    params = {"tf": TF, "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
              "rr": 2.0, "max_hold": HOLD}
    src = {"tf": "corpus: structure-requires-htf-context.yaml timeframes ltf 5m (htf 1D/1H)",
           "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    for reading, claim, rule, xp, xs in (
            ("a", "+", "reading a: keep events whose previous completed 18:00-NY daily candle "
                       "is a C2/C3 closure (detectors.bias.daily_closures, C3 ref = C2 open); "
                       "gate = CISD direction == that closure's direction",
             {"daily_anchor": "prior day C2/C3 closure", "day_open_hour": 18},
             {"daily_anchor": "corpus: yaml detection_rules 'Step 1: find a daily candle 2 "
                              "closure and take its direction'",
              "day_open_hour": "method_spec: §1.4 daily open 18:00 canon"}),
            ("b", "-", "reading b: gate = CISD close inside an opposing, still-open 1h FVG "
                       f"(wick 3-bar gap) created within the last {FVG_LB} closed 1h bars and "
                       "not traded through by any closed 1h bar since; claim '-' (these fail)",
             {"fvg_lookback_1h": FVG_LB},
             {"fvg_lookback_1h": "declared-before-run: one trading day of 1h bars"})):
        ev = cl.cache_frame(f"srhc_{reading}_{TF}_v1", lambda: detect(cl.load_m1(), reading))
        print(reading, len(ev), ev["gate"].mean())
        probe = cl.probe_lookahead(lambda m: detect(m, reading), ev, lookback="10D")
        res = cl.gate_test(ev, "gate", mask_available_at="decision_time", max_hold=HOLD,
                           claim=claim)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": base + [rule],
                                                "params": {**params, **xp}},
                            params_source={**src, **xs}, script=__file__, probe=probe,
                            notes="Gate inputs are closed daily / 1h bars only (asof the "
                                  "decision), so mask_available_at = decision_time.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
