"""invalidation-trade — update_20261007_live_05: the SOFT-invalidation claim (new reading).

Source (4rNC3QXxC20, New York Open Live Q&A):
  "just cuz it goes over the EQ doesn't automatically mean that it's going to go to previous
   day high. It's a soft invalidation. It means that it's gone too high to form a small wick to
   expand lower. ... if you have a large wick, you adjust where your targets would be around the
   daily open, liquidity around that"
  "A closure through the EQ does not equal switch bias. It can mean the invalidation of the bias
   when it's paired with other things along with the daily profile. ... there's nothing bullish
   in here. No structure."

Bias / EQ / aligned tf are reused exactly from the library reading (model_own_01a):
daily C2/C3 closure on D + same-direction 1h CISD inside D -> bias for D+1; EQ = midpoint of
D's range; first 1h close of D+1 beyond EQ against the bias = the EQ close.
"Opposing structure" = a 1h CISD in the opposite direction (series_open, 2/2, max_wait 3)
confirmed in the same session at or before the EQ-break bar. The daily-profile half of
"paired with" is discretionary and is not modelled.

Readings (claim '+'):
  u1007a  trade_test: EQ close WITHOUT opposing structure -> keep the original bias, enter at
          the break close, target = the daily open (18:00 NY), stop = session running extreme
          on the break side (the large wick), exit 17:00 NY.
  u1007b  same as u1007a but stop = prior day D's extreme on the break side (PDH for a bearish
          bias): "doesn't automatically mean that it's going to go to previous day high" — the
          hard invalidation is the prior-day extreme, not the wick. Declared after u1007a came
          back n=24 (the running-wick stop sits within 0.10 x D range of the break close on most
          days); the stop is the source's open parameter, the second of at most two readings.

AUDIT 2026-10-07 (vault-context re-run, same labels, same hypothesis), two fixes:
  1. The EQ close must be a CLOSE THROUGH the EQ: the session (D+1) must open on the bias side
     of the EQ. The first run also scored sessions that opened already beyond the EQ (29/157 in
     u1007b, 2/24 in u1007a), where price never "goes over" the EQ and the source's mechanism
     ("gone too high to form a small wick") does not exist.
  2. Control holds the NY clock (ctrl_tod_tol_min=30, README trap 9 / vault Concept Campaign
     lesson 3): not a timing concept, but 66% of u1007b decisions sit at 19:00-23:00 NY.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import (cl, np, pd, OHLC, c2c3_h1_bias, hourly_with_prior_day,  # noqa: E402
                     cisd_events, MIN_RISK_FRAC, MIN_DAY_M1)

READ = sys.argv[1] if len(sys.argv) > 1 else "u1007a"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold", "no_opp"]


def detect_all(m1, stop_mode="wick"):
    bd = c2c3_h1_bias(m1)
    h = hourly_with_prior_day(m1, bd)
    x = h[h["D_ok"].to_numpy() & h["D_bias"].isin(["bullish", "bearish"]).to_numpy()].copy()
    bull = (x["D_bias"] == "bullish").to_numpy()
    eq = ((x["D_high"] + x["D_low"]) / 2).to_numpy(float)
    opened_bias_side = np.where(bull, x["day_open"] > eq, x["day_open"] < eq)   # audit fix 1
    x = x[np.where(bull, x["close"] < eq, x["close"] > eq) & opened_bias_side]
    x = x[~x["tday"].duplicated(keep="first")]          # first EQ close of the session
    if x.empty:
        return pd.DataFrame(columns=COLS)
    ev = cisd_events(h[OHLC], level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
    ev = ev.assign(tday=cl.trading_day(pd.DatetimeIndex(ev["confirm_time"])))
    no_opp = []
    for t0, r in x.iterrows():
        opp = "bearish" if r["D_bias"] == "bullish" else "bullish"
        c = ev[(ev["tday"] == r["tday"]) & (ev["direction"] == opp)
               & (pd.DatetimeIndex(ev["confirm_time"]) <= t0)]
        no_opp.append(c.empty)
    bull = (x["D_bias"] == "bullish").to_numpy()
    sgn = np.where(bull, 1, -1)                         # KEEP the original bias
    c = x["close"].to_numpy(float)
    if stop_mode == "wick":
        stop = np.where(bull, x["run_low"], x["run_high"]).astype(float)
    else:
        stop = np.where(bull, x["D_low"], x["D_high"]).astype(float)
    tgt = x["day_open"].to_numpy(float)
    rng = (x["D_high"] - x["D_low"]).to_numpy(float)
    ct = pd.DatetimeIndex(x["close_time"])
    hold = pd.DatetimeIndex(x["day_end"]) - ct
    ok = ((sgn * (c - stop) >= MIN_RISK_FRAC * rng) & (sgn * (tgt - c) > 0)
          & (hold > pd.Timedelta(0)))
    out = pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": sgn,
                        "stop_px": stop, "target_px": tgt, "max_hold": hold,
                        "no_opp": np.array(no_opp, dtype=bool)})
    return out[ok].reset_index(drop=True)


def detect_a(m1):
    e = detect_all(m1)
    return e[e["no_opp"].astype(bool)].reset_index(drop=True)


def detect_b(m1):
    e = detect_all(m1, stop_mode="pdx")
    return e[e["no_opp"].astype(bool)].reset_index(drop=True)


detect, key = (detect_a, "softinv_a_cross") if READ == "u1007a" else (detect_b, "softinv_b_pdx_cross")
ev = cl.cache_frame(key, lambda: detect(cl.load_m1()))
ev["no_opp"] = ev["no_opp"].astype(bool)
print(READ, "events", len(ev), ev["direction"].value_counts().to_dict(), "no_opp", ev["no_opp"].mean())
probe = cl.probe_lookahead(detect, ev, lookback="20D")
print("probe", probe.get("passed"))
res = cl.trade_test(ev, hold_basis="bars", ctrl_tod_tol_min=30)
for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
          "ties", "exposure_bars", "ctrl_overlap", "halves"):
    print(k, res.get(k))

rules = ["bias: daily C2/C3 (C2-open ref) closure on D + same-direction 1h CISD inside D (scope range)",
         "EQ close: FIRST 1h close of session D+1 beyond EQ=(D high+D low)/2 against the bias, "
         "in a session that OPENED on the bias side of the EQ (a close through it)",
         "opposing structure: 1h CISD (series_open, 2/2, max_wait 3) opposite to the bias confirmed "
         "in session D+1 at/before the EQ-break bar; daily profile NOT modelled",
         "trade the ORIGINAL bias at the break close (next M1 open); target = session open (18:00 NY); "
         + ("stop = session running extreme on the break side through the break bar; " if READ == "u1007a"
            else "stop = prior day D's extreme on the break side (PDH for bearish bias); ")
         + "exit 17:00 NY; "
         "skip if stop < 0.10 x D range or open not beyond price"]
rules.append("only EQ closes WITHOUT opposing structure")
op = {"rules": rules,
      "params": {"eq": "50% of prior day range", "aligned_tf": "1h", "target": "daily open",
                 "stop": "session running extreme (the large wick)" if READ == "u1007a"
                         else "prior day extreme on the break side", "structure": "opposing 1h CISD",
                 "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                 "min_risk_frac": MIN_RISK_FRAC, "stub_filter_min_m1": MIN_DAY_M1,
                 "cisd_scope": "range", "c3_reference": "c2_open", "hold_basis": "bars",
                 "eq_cross": "session open on the bias side of the EQ", "ctrl_tod_tol_min": 30}}
src = {"eq": "corpus: 4rNC3QXxC20 'A closure through the EQ does not equal switch bias'",
       "aligned_tf": "corpus: invalidation-trade library ambiguity 'in the worked example the EQ was read on the hourly'",
       "target": "corpus: 4rNC3QXxC20 'you adjust where your targets would be around the daily open'",
       "stop": ("corpus: 4rNC3QXxC20 'This means it has a large wick' (the wick extreme is the invalidation point)"
                if READ == "u1007a" else "corpus: 4rNC3QXxC20 'doesn't automatically mean that it's going to go to "
                "previous day high' (PDH = the hard invalidation); declared after u1007a returned n=24"),
       "structure": "corpus: 4rNC3QXxC20 'there's nothing bullish in here. No structure.'",
       "level_rule": "phase3: locked CISD level rule", "swing": "phase3: locked swing 2/2",
       "max_wait": "phase3: locked max_wait=3",
       "min_risk_frac": "declared-before-run: degenerate-stop guard, _common.MIN_RISK_FRAC",
       "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions",
       "cisd_scope": "phase3: locked primary cisd_scope=range",
       "c3_reference": "phase3: locked primary C3 reference (Reading A)",
       "hold_basis": "declared-before-run: README trap 7; the sibling library readings of this exact "
                     "intraday frame showed >10% real/control exposure gaps on clock basis",
       "eq_cross": "corpus: 4rNC3QXxC20 'just cuz it goes over the EQ' / 'A closure through the EQ' / "
                   "'it's gone too high to form a small wick' (the wick from the open must cross the EQ); "
                   "audit fix, declared before the re-run",
       "ctrl_tod_tol_min": "declared-before-run: README trap 9 / vault Concept Campaign lesson 3 - not a timing "
                           "concept but decisions cluster at 19:00-23:00 NY (66% in the first run); audit fix"}
p = cl.write_result("invalidation-trade", READ, res, operationalization=op, params_source=src,
                    script=__file__, probe=probe,
                    notes="Tests ONLY the new soft-invalidation claim (update_20261007_live_05). "
                          "Daily-profile pairing is discretionary and not modelled. "
                          "AUDIT 2026-10-07 re-run: EQ close now requires a genuine close through the EQ "
                          "(session opened on the bias side) and the control holds the NY clock +/-30 min.")
print(p)
