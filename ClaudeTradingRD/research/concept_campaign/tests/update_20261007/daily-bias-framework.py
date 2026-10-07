"""daily-bias-framework — update 2026-10-07 (live_01 + live_03 drafts). NEW claims only.

Prior readings (__a daily / __b 4H previous-candle engine, trade tests) are untouched.

Baseline book (shared with daily-profile-confirmation, _common.intraday_bias_book): on the
session after a confirmed daily bias (daily C2/C3 closure + same-direction H1 CISD), at every
1h close 03:00-12:00 NY, go in the bias direction toward the prior day's bias-side extreme,
stop at the day's running opposite extreme, exit 17:00 NY.

Readings (gate_test, claim '+'):
  u1007a  daily-open invalidation (live_01, ES-R3ByDYrY): "I was bearish initially. that's
          gotten invalid for me is if we can get a closure over a daily open". Gate =
          bias still intact = NO 1h close beyond the 18:00 NY day open against the bias
          from the day start through the decision bar (once closed beyond, invalidated
          for the rest of the day). Applied symmetrically (mirror for a bullish bias).
  u1007b  one-sided vs two-sided (live_03, rVRk4MLTJSs): "This is a C3 daily candle.
          There's really only one way to frame this. That is one-sided" vs the two-sided
          day framed by a reversal "and we're in this continuation to C4". Gate = the
          traded day is a C3 daily candle (bias source day = C2 closure); complement =
          the traded day is a C4 (bias source day = C3 closure).

Not tested: the fallback list (OHLC / daily profile / phases of price; "use the intraday
profile or wait for the next day") — a menu of discretionary alternatives with no rule
for which applies; C3 closure as a fallback is already inside the baseline bias.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import (cl, np, pd, intraday_bias_book, c2c3_h1_bias,  # noqa: E402
                     MIN_RISK_FRAC, MIN_DAY_M1)

READ = sys.argv[1] if len(sys.argv) > 1 else "u1007a"
WIN = ("03:00", "12:00")


def detect_a(m1):
    ev = intraday_bias_book(m1, WIN)
    h = cl.build_bars(m1, "1h")[["open", "close"]].copy()
    h["tday"] = cl.trading_day(h.index)
    g = h.groupby("tday", sort=False)
    day_open = g["open"].transform("first")
    h["max_c"] = g["close"].cummax() - day_open     # through this (closed) 1h bar
    h["min_c"] = g["close"].cummin() - day_open
    x = h.reindex(pd.DatetimeIndex(ev["x_bar_start"]))
    bull = ev["direction"].to_numpy() > 0
    invalid = np.where(bull, x["min_c"].to_numpy() < 0, x["max_c"].to_numpy() > 0)
    ev["bias_intact"] = ~invalid
    return ev


def detect_b(m1):
    ev = intraday_bias_book(m1, WIN)
    d = c2c3_h1_bias(m1)
    src = cl.asof(d[["closure_kind", "close_time"]], pd.DatetimeIndex(ev["x_bar_start"]))
    ev["c3_day"] = (src["closure_kind"] == "C2").to_numpy()
    return ev


if READ == "u1007a":
    detect, key, gate = detect_a, "dbf_u1007a_open_inval", "bias_intact"
else:
    detect, key, gate = detect_b, "dbf_u1007b_c3_vs_c4", "c3_day"

ev = cl.cache_frame(key, lambda: detect(cl.load_m1()))
print(READ, "events", len(ev), "gated", int(ev[gate].sum()), "days", ev["x_tday"].nunique())
probe = cl.probe_lookahead(detect, ev, lookback="20D")
print("probe", probe.get("passed"))
res = cl.gate_test(ev, gate, mask_available_at="decision_time")
for k in ("n", "n_gated", "gate_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
          "verdict_detail", "ties", "ctrl_overlap", "halves"):
    print(k, res.get(k))

base_rules = [
    "bias: daily C2 or C3 (C2-open reference) closure + same-direction 1h CISD inside that "
    "day (series_open, scope range) -> bias for the next session",
    "baseline: next session, every 1h close with NY close time in 03:00-12:00; direction = "
    "bias; stop = day's running opposite extreme; target = prior day's bias-side extreme; "
    "exit 17:00 NY; drop rows where the target was already reached, target not beyond "
    "price, or stop distance < 0.10 x prior-day range"]
params = {"window": "03:00-12:00 NY (1h closes)", "min_risk_frac": MIN_RISK_FRAC,
          "stub_filter_min_m1": MIN_DAY_M1, "cisd_scope": "range", "c3_reference": "c2_open",
          "day_open": "18:00 NY"}
src = {"window": "corpus: daily-profile-session-windows London 02:00-05:00 / NY a.m. 08:30-12:00 "
                 "(method_spec §2.5); same baseline as daily-profile-confirmation",
       "min_risk_frac": "declared-before-run: degenerate-stop guard, _common.MIN_RISK_FRAC",
       "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions",
       "cisd_scope": "phase3: locked primary cisd_scope=range",
       "c3_reference": "phase3: locked primary C3 reference (Reading A)",
       "day_open": "method_spec: §1.4 daily open is 18:00 (canon); library ambiguity notes the open is unstated"}
if READ == "u1007a":
    rules = base_rules + [
        "gate bias_intact: no 1h close since the 18:00 NY day open (through the decision bar) "
        "beyond the day open against the bias (bearish: close > open invalidates; mirror "
        "bullish); once invalidated, stays invalid for the day"]
    params.update(closure_tf="1h", invalidation_persistence="rest of day", symmetric=True)
    src.update(closure_tf="declared-before-run: draft ambiguity 'timeframe of the daily-open closure ... not "
                          "stated (chart shown was intraday)'; 1h = the book's own decision bars",
               invalidation_persistence="corpus: ES-R3ByDYrY 'I was bearish initially. that's gotten invalid "
                                        "for me is if we can get a closure over a daily open'",
               symmetric="declared-before-run: source shows the bearish case only; mirror applied")
    notes = "Tests only the daily-open closure invalidation (live_01). Fallback menu untested (discretionary)."
else:
    rules = base_rules + [
        "gate c3_day: the bias-source day (last daily close <= the 1h bar start) is a C2 "
        "closure, so the traded day is a C3 daily candle (one-sided); complement = bias "
        "source is a C3 closure, traded day is a C4 (two-sided continuation context)"]
    params.update(one_sided="traded day = C3 (source C2)", two_sided="traded day = C4 (source C3)")
    src.update(one_sided="corpus: rVRk4MLTJSs 'This is a C3 daily candle. There's really only one way to "
                         "frame this. That is one-sided'",
               two_sided="corpus: rVRk4MLTJSs 'You could frame it bullish because of the reversal ... "
                         "and we're in this continuation to C4. So I can really frame it both ways'")
    notes = ("Two-sidedness is operationalised as the C4 day only; the reversal-plus-failed-"
             "continuation read is a discretionary framing with no stated rule.")
p = cl.write_result("daily-bias-framework", READ, res, operationalization={"rules": rules, "params": params},
                    params_source=src, script=__file__, probe=probe, notes=notes)
print(p)
