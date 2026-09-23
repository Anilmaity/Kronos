"""wick-scenario-difficulty-ladder (model, TTrades own voice, specified).

Claim: of the three ways to trade a reversal, tier 1 (let the large-wick reversal candle
close, trade candle 3 when C3 respects the wick and prints a lower-timeframe CISD) is the
easiest/best and tier 3 (trade the large-wick daily reversal candle itself, on lower
timeframes, back toward the daily open) is the worst.

gate_test on the union of the two decidable tiers (daily HTF, 1h execution; bullish shown,
bearish mirrors), each first-per-day, entry at the 1h CISD close, stop at its protected swing,
flat 17:00 NY:
  tier 1: yesterday was a daily C2 (swept the prior day's low, closed back above it) with a
          LARGE wick (opposing run open->low > body, i.e. ratio > 1.0); today (C3) a 1h CISD
          in the C2 direction whose extreme holds above 0.5 of C2's wick; target 2R.
  tier 3: today is itself the reversal candle — it has taken the previous day's low, a 1h
          CISD confirms off today's low while price is still below the daily open; target =
          the daily open (same construction as reversal-candle-target-adjustment reading a).
gate = tier 1; claim '+'. Tier 2 (reversal-to-expansion candle) needs the candle's final wick
size, which is unknowable live, so it is not isolated.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import importlib.util
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C

RR = 2.0
WICK_CUT = 1.0


def _rcta():
    spec = importlib.util.spec_from_file_location(
        "rcta", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/"
                "model_own_02b/reversal-candle-target-adjustment.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


RCTA = _rcta()


def tier1(m1):
    d = C.daily(m1).reset_index(drop=True)
    pl, ph = d["low"].shift(1), d["high"].shift(1)
    o, c, lo, hi = d["open"], d["close"], d["low"], d["high"]
    body = (c - o).abs()
    bull = (lo < pl) & (c > pl) & ((o - lo) > WICK_CUT * body)
    bear = (hi > ph) & (c < ph) & ((hi - o) > WICK_CUT * body)
    half_b = lo + (np.minimum(o, c) - lo) / 2
    half_s = hi - (hi - np.maximum(o, c)) / 2
    c2 = pd.DataFrame({"td": d["td"], "bull": bull, "bear": bear,
                       "half_b": half_b, "half_s": half_s})
    c2 = c2[(c2["bull"] ^ c2["bear"])]
    h = C.complete_bars(m1, "1h")
    cz = C.cisd_table(h)
    cz = cz.assign(td=cl.trading_day(cz["t"]))
    cz = cz[cl.trading_day(cz["extreme_start"]) == cz["td"]]
    # yesterday = the previous complete session
    prev_td = C.prev_day_levels(d.set_index(d["td"]).rename_axis(None), cz["td"])["pd_td"].to_numpy()
    cz["prev_td"] = prev_td
    m = cz.merge(c2, left_on="prev_td", right_on="td", how="inner", suffixes=("", "_c2"))
    okb = m["bull"] & (m["dir"] == 1) & (m["extreme_price"] > m["half_b"])
    oks = m["bear"] & (m["dir"] == -1) & (m["extreme_price"] < m["half_s"])
    q = m[(okb | oks).to_numpy()].sort_values("t").groupby("td", sort=True).head(1)
    t = pd.DatetimeIndex(q["t"])
    ent = q["confirm_close"].to_numpy(float); stp = q["stop"].to_numpy(float)
    return pd.DataFrame({"decision_time": t, "available_at": t,
                         "direction": q["dir"].astype(int).to_numpy(), "stop_px": stp,
                         "target_px": ent + RR * (ent - stp),
                         "max_hold": C.session_end(t) - t, "tier1": True})


def detect(m1):
    a = tier1(m1)
    b = RCTA.detect(m1, target="open").assign(tier1=False)
    out = pd.concat([a, b], ignore_index=True)
    out = out[out["max_hold"] > pd.Timedelta(0)]
    out = out.sort_values(["decision_time", "tier1"], kind="stable").reset_index(drop=True)
    out["tier1"] = out["tier1"].astype(bool)
    out["direction"] = out["direction"].astype(int)
    return out


if __name__ == "__main__":
    ev = cl.cache_frame("wsdl_events_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["tier1"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    r = cl.gate_test(ev, "tier1", mask_available_at="decision_time", max_hold=None)
    print({k: r.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars")})
    params = {"exec_tf": "1h", "cisd": "series_open, swing 2/2, max_wait 3",
              "c2_test": "sweep prior day extreme, close back inside", "wick_cut": WICK_CUT,
              "half_wick": "C3 CISD extreme holds beyond 0.5 of C2's wick (body->extreme)",
              "tier1_target_rr": RR, "tier3_target": "daily 18:00 open",
              "tier3_def": "today took PDL/PDH, 1h CISD off today's extreme, price still beyond the open",
              "exit": "17:00 NY session close", "one_per_day_per_tier": True}
    src = {"exec_tf": "corpus: SlWxhzhLo3A 'a reversal candle on the daily, then I look to trade the lower time frames'",
           "cisd": "phase3: locked CISD config",
           "c2_test": "method_spec: §3.2 C2 test",
           "wick_cut": "threshold_fits: small/large wick opposing_run/body crossover 1.0 (grade A)",
           "half_wick": "method_spec: §3.2 'If C2 has a large wick, mark 0.5 of the wick — C3's wick must respect that half'",
           "tier1_target_rr": "method_spec: §5.3 2R",
           "tier3_target": "corpus: SlWxhzhLo3A tier 3 'executed on lower timeframes back toward the daily open'",
           "tier3_def": "declared-before-run: same construction as reversal-candle-target-adjustment reading a",
           "exit": "declared-before-run: trade inside the current daily candle",
           "one_per_day_per_tier": "method_spec: §2.4 one CISD per day"}
    cl.write_result("wick-scenario-difficulty-ladder", None, r,
                    operationalization={"rules": [
                        "tier 1: prior daily C2 with opposing run > body; today a 1h CISD in its "
                        "direction holding 0.5 of C2's wick; 2R; flat 17:00 NY",
                        "tier 3: today takes PDL/PDH, a 1h CISD off today's extreme with price "
                        "still beyond the daily open; target the daily open; flat 17:00 NY",
                        "gate = tier 1 vs tier 3 (control-adjusted); claim '+'"],
                        "params": params},
                    params_source=src, script=__file__, probe=probe,
                    notes="Tier 2 not isolable live (needs the final wick size of the candle "
                          "in progress). Tier 1's 'C3 small wick' is operationalised by the "
                          "stated half-wick respect rule.")
