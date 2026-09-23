"""daily-profile-confirmation — Daily Profile Must Confirm the Daily Bias (contested).

Claim ('+'): with a daily bias established (daily C2/C3 + H1 CISD — precondition 2), a
bias-direction trade is better once the day's profile CONFIRMS: "Bullish confirmation:
price opens, forms a low (ideally a shallow sweep), then trends higher" (mirror
bearish); "Non-confirmation: price opens and immediately expands into objectives without
forming the opposing extreme first" -> "look for a move back to the daily open", i.e.
bias trades should do worse there.

Test: gate_test on a baseline book (state it): on the session after a confirmed daily
bias, at every 1h close from 03:00 to 12:00 NY (London open through the NY-AM window
of daily-profile-session-windows), go in the bias direction toward the prior day's
bias-side extreme, stop at the day's running opposite extreme, exit 17:00 NY
(_common.intraday_bias_book). Rows where the draw is already reached are dropped (the
bias is spent).

Gate (known at the 1h close, pass or fail): the day has FORMED ITS OPPOSING EXTREME —
opposing run from the day's 18:00 open to the running low (bullish) is more than 0.30
of the day's running range (threshold_fits: 'small wick' range parameterisation cut
0.30 = the expansion candle / 'no low to trade away from') — AND price is now trending
in the bias direction (close beyond the day open).

Single reading: the concept's own contest ("confirm or invalidate is never given a
test") is about the invalidation side, which has no rule; the confirmation side
above is the only decidable reading.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import cl, np, intraday_bias_book, MIN_RISK_FRAC, MIN_DAY_M1  # noqa: E402

WIN = ("03:00", "12:00")
CUT = 0.30


def detect(m1):
    ev = intraday_bias_book(m1, WIN)
    bull = ev["direction"].to_numpy() > 0
    rng = (ev["x_run_high"] - ev["x_run_low"]).to_numpy(float)
    opp = np.where(bull, ev["x_day_open"] - ev["x_run_low"], ev["x_run_high"] - ev["x_day_open"])
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(rng > 0, opp / rng, 0.0)
    trending = np.where(bull, ev["x_close"] > ev["x_day_open"], ev["x_close"] < ev["x_day_open"])
    ev["profile_confirmed"] = (ratio > CUT) & trending
    return ev


ev = cl.cache_frame("dpc_profile_gate", lambda: detect(cl.load_m1()))
print("events", len(ev), "gated", int(ev["profile_confirmed"].sum()), "days", ev["x_tday"].nunique())
probe = cl.probe_lookahead(detect, ev, lookback="20D")
print("probe", probe.get("passed"))
res = cl.gate_test(ev, "profile_confirmed", mask_available_at="decision_time")
for k in ("n", "n_gated", "gate_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
          "ties", "exposure_bars", "ctrl_overlap", "halves", "dependence"):
    print(k, res.get(k))

op = {"rules": [
    "bias: daily C2 or C3 (C2-open reference) closure + same-direction 1h CISD inside that "
    "day (series_open, scope range) -> bias for the next session",
    "baseline: next session, every 1h close with NY close time in 03:00-12:00; direction = "
    "bias; stop = day's running opposite extreme; target = prior day's bias-side extreme; "
    "exit 17:00 NY; drop rows where the target was already reached, target not beyond "
    "price, or stop distance < 0.10 x prior-day range",
    "gate: (day open - running low)/(running high - running low) > 0.30 for a bullish bias "
    "(mirror bearish) AND close beyond the day open in the bias direction",
    "gate is computed from closed 1h bars at the decision time (mask_available_at = decision)"],
    "params": {"window": "03:00-12:00 NY (1h closes)", "opposing_run_cut_range": CUT,
               "min_risk_frac": MIN_RISK_FRAC, "stub_filter_min_m1": MIN_DAY_M1,
               "cisd_scope": "range", "c3_reference": "c2_open", "day_open": "18:00 NY"}}
src = {"window": "corpus: daily-profile-session-windows London 02:00-05:00 / NY a.m. 08:30-12:00 "
                 "(method_spec §2.5); first 1h close after the London open to the NY-AM end",
       "opposing_run_cut_range": "threshold_fits: small wick range parameterisation opposing_run/(high-low) <= 0.30 (grade C)",
       "min_risk_frac": "declared-before-run: degenerate-stop guard, _common.MIN_RISK_FRAC",
       "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions",
       "cisd_scope": "phase3: locked primary cisd_scope=range",
       "c3_reference": "phase3: locked primary C3 reference (Reading A)",
       "day_open": "method_spec: §1.4 daily open is 18:00 (canon)"}
p = cl.write_result("daily-profile-confirmation", None, res, operationalization=op,
                    params_source=src, script=__file__, probe=probe,
                    notes="Invalidation side ('what would count as invalidation is never given') "
                          "is not operationalised; only the stated confirmation shape is gated.")
print(p)
