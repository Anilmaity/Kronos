"""invalidation-trade — Invalidation Trade: trading the failure of a valid model (contested).

Claim ('+'): when a genuinely valid model (candle 2 closure + change in the state of
delivery) fails at its own EQ — price closes beyond the EQ of the previous
higher-timeframe candle on the aligned lower timeframe (Case 2) — the trade in the
OPPOSITE direction toward the opposing liquidity (the previous day low/high) pays.

Valid model: daily C2 or C3 closure on day D + same-direction 1h CISD inside D
(daily-bias-c2-c3-h1-cisd, phase3 primary config) -> expected direction for D+1.
EQ = 50% of D's range ('the EQ of our previous candle'); aligned timeframe = 1h (the
worked example 'read the EQ on the hourly'). Target = D's opposite extreme (previous
day low for a failed bullish model). Exit at 17:00 NY of D+1.

Readings (contested: whether the EQ close itself is the entry):
  a  enter at the FIRST 1h close beyond D's EQ against the model; stop at the session's
     running extreme on the model's side (execution.stop 'stops on the high').
  b  "the invalidation itself is not the entry": after that EQ close, wait for a 1h
     CISD in the NEW direction (detectors.cisd, series_open, 2/2, max_wait 3) confirming
     at or after the EQ-break bar within the same session; enter at its close; stop at
     its protected swing.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import (cl, np, pd, OHLC, c2c3_h1_bias, hourly_with_prior_day,  # noqa: E402
                     cisd_events, MIN_RISK_FRAC, MIN_DAY_M1)

READ = sys.argv[1] if len(sys.argv) > 1 else "a"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]


def eq_breaks(m1):
    bd = c2c3_h1_bias(m1)
    h = hourly_with_prior_day(m1, bd)
    x = h[h["D_ok"].to_numpy() & h["D_bias"].isin(["bullish", "bearish"]).to_numpy()].copy()
    bull = (x["D_bias"] == "bullish").to_numpy()
    eq = ((x["D_high"] + x["D_low"]) / 2).to_numpy(float)
    brk = np.where(bull, x["close"] < eq, x["close"] > eq)
    x = x[brk]
    x = x[~x["tday"].duplicated(keep="first")]          # the first EQ close of the session
    return h, x


def detect_a(m1):
    _, x = eq_breaks(m1)
    bull = (x["D_bias"] == "bullish").to_numpy()        # the FAILED model's direction
    sgn = np.where(bull, -1, 1)                         # trade the opposite way
    c = x["close"].to_numpy(float)
    stop = np.where(bull, x["run_high"], x["run_low"]).astype(float)
    tgt = np.where(bull, x["D_low"], x["D_high"]).astype(float)
    rng = (x["D_high"] - x["D_low"]).to_numpy(float)
    ct = pd.DatetimeIndex(x["close_time"])
    hold = pd.DatetimeIndex(x["day_end"]) - ct
    ok = ((sgn * (c - stop) >= MIN_RISK_FRAC * rng) & (sgn * (tgt - c) > 0)
          & (hold > pd.Timedelta(0)))
    out = pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": sgn,
                        "stop_px": stop, "target_px": tgt, "max_hold": hold})
    return out[ok].reset_index(drop=True)


def detect_b(m1):
    h, x = eq_breaks(m1)
    ev = cisd_events(h[OHLC], level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
    if ev.empty or x.empty:
        return pd.DataFrame(columns=COLS)
    ev = ev.assign(tday=cl.trading_day(pd.DatetimeIndex(ev["confirm_time"])))
    rows = []
    for t0, r in x.iterrows():
        new_dir = "bearish" if r["D_bias"] == "bullish" else "bullish"
        cand = ev[(ev["tday"] == r["tday"]) & (ev["direction"] == new_dir)
                  & (pd.DatetimeIndex(ev["confirm_time"]) >= t0)]
        if cand.empty:
            continue
        e = cand.iloc[0]
        ct = h.loc[e["confirm_time"], "close_time"]
        rows.append({"decision_time": ct, "available_at": ct,
                     "direction": -1 if new_dir == "bearish" else 1,
                     "stop_px": float(e["protected_swing"]),
                     "target_px": float(r["D_low"] if new_dir == "bearish" else r["D_high"]),
                     "max_hold": r["day_end"] - ct,
                     "_c": float(h.loc[e["confirm_time"], "close"])})
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=COLS)
    ok = (out["direction"] * (out["target_px"] - out["_c"]) > 0) & (out["max_hold"] > pd.Timedelta(0))
    return out[ok][COLS].reset_index(drop=True)


detect, key = (detect_a, "inv_a_eqclose") if READ == "a" else (detect_b, "inv_b_eq_then_cisd")
ev = cl.cache_frame(key, lambda: detect(cl.load_m1()))
print(READ, "events", len(ev), ev["direction"].value_counts().to_dict())
probe = cl.probe_lookahead(detect, ev, lookback="20D")
print("probe", probe.get("passed"))
res = cl.trade_test(ev, hold_basis="bars")
for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
          "ties", "exposure_bars", "ctrl_overlap", "halves"):
    print(k, res.get(k))

base = ["valid model: daily C2/C3 (C2-open ref) closure on day D + same-direction 1h CISD "
        "inside D (scope range, series_open)",
        "invalidation: FIRST 1h close of session D+1 beyond EQ = (D high + D low)/2 against "
        "the model direction",
        "trade opposite to the model; target = D's opposite extreme (PDL for a failed bullish "
        "model); exit at 17:00 NY of D+1 (wall clock)"]
if READ == "a":
    op = {"rules": base + ["enter at that 1h close (next M1 open); stop = session running "
                           "high (failed bullish model) / low, through the break bar; skip "
                           "if stop distance < 0.10 x D range or target not beyond price"],
          "params": {"eq": "50% of prior day range", "aligned_tf": "1h", "entry": "EQ-break close",
                     "min_risk_frac": MIN_RISK_FRAC, "stub_filter_min_m1": MIN_DAY_M1,
                     "cisd_scope": "range", "c3_reference": "c2_open", "hold_basis": "bars"}}
else:
    op = {"rules": base + ["after the EQ-break bar, the first 1h CISD in the NEW direction "
                           "(series_open, 2/2 swing, max_wait 3) whose confirm bar starts at "
                           "or after the break bar in the same session; enter at its close; "
                           "stop = its protected swing"],
          "params": {"eq": "50% of prior day range", "aligned_tf": "1h", "entry": "CISD after EQ break",
                     "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                     "stub_filter_min_m1": MIN_DAY_M1, "cisd_scope": "range", "c3_reference": "c2_open",
                     "hold_basis": "bars"}}
src = {"eq": "corpus: invalidation-trade 'closes beyond the EQ of the previous higher-timeframe candle'",
       "aligned_tf": "corpus: invalidation-trade ambiguity 'in the worked example the EQ was read on the hourly'",
       "entry": "corpus: invalidation-trade execution.entry (a) / detection 'the invalidation itself is not the entry' (b)",
       "min_risk_frac": "declared-before-run: degenerate-stop guard, _common.MIN_RISK_FRAC",
       "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions",
       "cisd_scope": "phase3: locked primary cisd_scope=range",
       "c3_reference": "phase3: locked primary C3 reference (Reading A)",
       "level_rule": "phase3: locked CISD level rule", "swing": "phase3: locked swing 2/2",
       "max_wait": "phase3: locked max_wait=3",
       "hold_basis": "declared-before-run: README trap 7 procedure — clock runs showed real/control exposure 795/716 (a) and 706/640 (b) bars (>10%), rerun with bars"}
src = {k: v for k, v in src.items() if k in op["params"]}
p = cl.write_result("invalidation-trade", READ, res, operationalization=op, params_source=src,
                    script=__file__, probe=probe,
                    notes="Case 1 (opposing setup at the previous-day extreme) is not included; "
                          "'fails to reclaim' is not required at entry (unknowable then). RE-RUN NOTE: "
                          "first runs with hold_basis=clock: a diff +0.039 [-0.060,+0.140] "
                          "UNDERPOWERED; b diff -0.029 [-0.148,+0.092] UNDERPOWERED; exposure gap "
                          ">10% so re-run once with hold_basis='bars' per README trap 7.")
print(p)
