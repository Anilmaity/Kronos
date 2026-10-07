"""update_20261007 / daily-profile-confirmation -- NEW claim only (draft live_12), vault-context rerun.

Source rTomJ8URFnw (New York Open Live Q&A), indices worked live: "NASDAQ into all-time
highs, multiple days of expansion ... on the hour, right? Kind of just failure swings up
mostly. Yeah, that's not quite bullish in terms of daily profile", "normally on a day like
this, you either consolidate or you have a reversal. That's why I'm favoring the downside
inside the daily profile because we just have failure swings. Usually, you have 930 some
sort of manipulation and a move lower", "I can't trade long when my daily profile looks
like this and we've already expanded right over previous highs".

Claim: after an OVERNIGHT expansion over previous highs with only failure swings up on the
hourly, do not frame longs (expect a reversal lower or consolidation). Mirror applied.

Book (one event per trading day, 18:00 NY roll): decision 09:30 NY. Universe = days whose
overnight hourly bars (closed by 09:30) include a CLOSE beyond the prior real session's high
(-> continuation LONG) or low (-> SHORT); both/neither dropped; at least MIN_POST hourly bars
after the expansion bar so a post-expansion profile exists. Continuation trade: stop = day's
running opposite extreme at 09:30, 2R, exit 17:00 NY; drop risk < 0.10 x prior-day range.

"Failure swing" is CONTESTED in the library (concepts/structure/failure-swing.yaml); one
reading per definition, both declared before the run (claim '-': gated continuation worse):
  u1007v12a  expansion-based ("swing highs ... that failed to expand"): no post-expansion
             hourly CLOSE beyond the running session extreme (wick-only takes count as failures).
  u1007v12b  sweep-based ("approached and turned away from WITHOUT taking it out"): no
             post-expansion hourly bar trades beyond the running extreme at all.
Vault-driven changes vs the no-vault readings u1007l12a/b (kept, not overwritten; their script
is preserved in _prior_novault/): those counted a sweep-and-close-back as THE failure swing and
dropped days with no new extreme -- which the sweep-based definition calls the purest failure
swings; and the control now holds the NY clock (README trap 9, vault Session Timing on Gold:
09:30 is gold's volatility step; campaign lesson 3).
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

CID = "daily-profile-confirmation"
NY = "America/New_York"
DEC = (9, 30)            # decision 09:30 NY
MIN_H1 = 12              # of the 15 overnight 1h bars 18:00 -> 09:00
MIN_POST = 2             # hourly bars after the expansion bar (a swing needs a following bar)
MIN_DAY_M1 = 600         # stub-session filter for the prior day (README trap 6)
MIN_RISK_FRAC = 0.10
RR = 2.0
MAX_HOLD = "450min"      # 09:30 -> 17:00 NY, no halt inside
TOD_TOL = 30
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr",
        "no_expand", "no_new_ext", "x_npost", "x_nfail", "x_nsucc"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    h = cl.build_bars(m1, "1h")
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_DAY_M1]
    if h.empty or d.empty:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})
    td = cl.trading_day(h.index)
    days = pd.DatetimeIndex(np.unique(td.to_numpy()))
    dec = (days + pd.Timedelta(days=1, hours=DEC[0], minutes=DEC[1])).tz_localize(NY).tz_convert("UTC")
    prev = cl.asof(d[["high", "low", "close_time", "trading_day"]], dec)
    gap = (days - pd.DatetimeIndex(prev["trading_day"])).days.to_numpy()
    pdh, pdl = prev["high"].to_numpy(float), prev["low"].to_numpy(float)

    hi, lo, cl_ = (h[k].to_numpy(float) for k in ("high", "low", "close"))
    ct = pd.DatetimeIndex(h["close_time"]).tz_convert("UTC").asi8
    tdn = td.asi8
    m1_close = pd.Series(m1["close"].to_numpy(float), index=pd.DatetimeIndex(m1.index).tz_convert("UTC"))
    rows = []
    for k, day in enumerate(days):
        if not (1 <= gap[k] <= 4) or not np.isfinite(pdh[k]):
            continue
        idx = np.flatnonzero((tdn == day.value) & (ct <= dec[k].value))   # 1h bars CLOSED by 09:30
        if len(idx) < MIN_H1:
            continue
        H, L, C = hi[idx], lo[idx], cl_[idx]
        up = np.flatnonzero(C > pdh[k])
        dn = np.flatnonzero(C < pdl[k])
        if (len(up) > 0) == (len(dn) > 0):        # neither, or both sides expanded
            continue
        s = 1 if len(up) else -1
        e = (up if s == 1 else dn)[0]
        if len(idx) - e - 1 < MIN_POST:
            continue
        ext = H[:e + 1].max() if s == 1 else L[:e + 1].min()
        nf = ns = 0
        for j in range(e + 1, len(idx)):
            if (H[j] > ext) if s == 1 else (L[j] < ext):          # trades beyond the running extreme
                if (C[j] > ext) if s == 1 else (C[j] < ext):      # ... and closes beyond: expansion
                    ns += 1
                else:                                             # ... wick only: failed to expand
                    nf += 1
                ext = H[j] if s == 1 else L[j]
        rows.append((dec[k], s, len(idx) - e - 1, nf, ns, pdh[k] - pdl[k]))
    if not rows:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})
    r = pd.DataFrame(rows, columns=["t", "s", "npost", "nf", "ns", "rng"])
    t = pd.DatetimeIndex(r["t"])
    ref = m1_close.reindex(t - pd.Timedelta(minutes=1)).to_numpy()   # 09:29 bar, closed at 09:30
    run = cl.running_hilo(t, "1D", m1=m1)
    s = r["s"].to_numpy()
    stop = np.where(s == 1, run["low"].to_numpy(float), run["high"].to_numpy(float))
    risk = s * (ref - stop)
    keep = np.isfinite(ref) & np.isfinite(stop) & (risk > 0) & (risk >= MIN_RISK_FRAC * r["rng"].to_numpy())
    ns_, nf_ = r["ns"].to_numpy(), r["nf"].to_numpy()
    ev = pd.DataFrame({"decision_time": t, "available_at": t, "direction": s, "stop_px": stop, "rr": RR,
                       "no_expand": ns_ == 0, "no_new_ext": (ns_ == 0) & (nf_ == 0),
                       "x_npost": r["npost"].to_numpy(), "x_nfail": nf_, "x_nsucc": ns_})
    return ev[keep].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("dpc_u1007v12_overnight_exp_failswing_minpost2", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict(),
          "no_expand", int(ev["no_expand"].sum()), "no_new_ext", int(ev["no_new_ext"].sum()))
    if "--power" in sys.argv:          # trap 6: power before interpretation (no test is run)
        sd = 0.8 * np.sqrt(1 + 1 / 5)  # per-trade R sd ~0.8 (u1007l12 books) + 5-draw control noise
        for g in ("no_expand", "no_new_ext"):
            ng = int(ev[g].sum()); nc = len(ev) - ng
            print(g, "gated", ng, "complement", nc, "approx MDE", round(2.8 * sd * np.sqrt(1 / ng + 1 / nc), 3))
        sys.exit(0)
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    base_rules = [
        "trading day rolls 18:00 NY; decision 09:30 NY (one event per day); available_at = decision "
        "(1h bars closed by 09:00, M1 closed by 09:30)",
        "prior day = last completed 18:00-NY session with >= 600 M1 bars, 1-4 calendar days back; PDH/PDL its high/low",
        "overnight = the day's 1h bars closed by 09:30 (>= 12 of 15 required)",
        "expansion: first overnight 1h CLOSE above PDH (long continuation) or below PDL (short); days with "
        "both or neither are dropped; >= 2 hourly bars after the expansion bar required (else no profile to read)",
        "after the expansion bar, a 1h bar trading beyond the running session extreme either closes beyond it "
        "(expansion) or closes back inside (failed to expand); the running extreme then moves to that bar's extreme",
        "trade: continuation direction, entry next M1 open at/after 09:30, stop = day's running opposite extreme "
        "(M1 closed by 09:30), 2R target, time exit 17:00 NY (450 min); drop risk < 0.10 x prior-day range",
        "control holds the NY clock: draws at 09:00/09:30/10:00 NY on other days within +/-30 days",
        "claim '-': continuation trades on gated days do worse than on complement days (control-adjusted)"]
    params = {"decision": "09:30 NY", "overnight_min_h1": MIN_H1, "min_post_bars": MIN_POST,
              "stub_day_min_n_m1": MIN_DAY_M1, "expansion": "1h close beyond PDH/PDL", "swing_tf": "1h",
              "mirror": True, "stop": "day running opposite extreme", "rr": RR, "max_hold": MAX_HOLD,
              "min_risk_frac": MIN_RISK_FRAC, "day_roll": "18:00 NY", "grid4h": "n/a",
              "ctrl_tod_tol_min": TOD_TOL}
    src = {"decision": "corpus: rTomJ8URFnw 'Usually, you have 930 some sort of manipulation and a move lower' "
                       "(vault Concept Campaign: on gold the volatility step is 09:30 NY)",
           "overnight_min_h1": "declared-before-run: data-hole guard on the overnight hourly sequence",
           "min_post_bars": "declared-before-run: plural 'failure swings'; a swing needs a later bar, rTomJ8URFnw "
                            "'candle 2 is always going to be the low or the high of a swing point'",
           "stub_day_min_n_m1": "declared-before-run: README trap 6 stub sessions (same cut as model_own_01a/_common)",
           "expansion": "corpus: rTomJ8URFnw 'we've already expanded right over previous highs'; method_spec / "
                        "threshold_fits: 'strong grades the close, not the wick' -> expansion = 1h close; 'previous "
                        "highs' read as the prior session high (the all-time-high variant is index-specific)",
           "swing_tf": "corpus: rTomJ8URFnw 'on the hour, right? Kind of just failure swings up mostly'",
           "mirror": "declared-before-run: source shows the upside case only; mirror applied",
           "stop": "method_spec: stop is the protected swing; day's running opposite extreme as in model_own_01a baseline",
           "rr": "method_spec: §5.3 2R fixed target (no target named for the vetoed long)",
           "max_hold": "corpus: rTomJ8URFnw 'normally on a day like this, you either consolidate or you have a "
                       "reversal' (the rest of the daily candle, to the 17:00 NY halt)",
           "min_risk_frac": "declared-before-run: degenerate-stop guard, model_own_01a/_common.MIN_RISK_FRAC",
           "day_roll": "session_window_fit: settled 18:00 NY daily roll",
           "grid4h": "declared-before-run: no 4h bars used",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9 (every event at 09:30 NY, concept not about timing) "
                               "+ session_window_fit / vault Session Timing on Gold + campaign lesson 3 (match time of day)"}
    readings = {
        "u1007v12a": ("no_expand",
                      "gate no_expand: no post-expansion 1h close beyond the running session extreme (every attempt "
                      "failed to expand)",
                      "corpus: rTomJ8URFnw 'because we just have failure swings'; library failure-swing.yaml "
                      "(contested) expansion definition 'swing highs ... that failed to expand'"),
        "u1007v12b": ("no_new_ext",
                      "gate no_new_ext: no post-expansion 1h bar trades beyond the running session extreme (later "
                      "highs turn away without taking it out)",
                      "corpus: rTomJ8URFnw 'Kind of just failure swings up mostly'; library failure-swing.yaml "
                      "(contested) sweep definition 'approached and turned away from WITHOUT taking it out'"),
    }
    for rd, (gate, rule, gsrc) in readings.items():
        res = cl.gate_test(ev, gate, mask_available_at="decision_time", max_hold=MAX_HOLD, claim="-",
                           ctrl_tod_tol_min=TOD_TOL)
        for k in ("n", "n_complement", "gate_firing_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "halves"):
            print(rd, k, res.get(k))
        p = cl.write_result(CID, rd, res, operationalization={"rules": base_rules + [rule],
                                                                "params": {**params, "gate": gate}},
                            params_source={**src, "gate": gsrc}, script=__file__, probe=probe,
                            notes="Vault-context rerun of draft live_12 (rTomJ8URFnw, indices example; the source's "
                                  "own outcome contradicted the framing). Readings u1007l12a/b (no vault context) are "
                                  "kept; their script is in _prior_novault/. Changes: the contested failure-swing "
                                  "definitions from the library replace the 'only/mostly' split, days with no new "
                                  "extreme are kept (sweep-based failure swings), the control holds the NY clock. "
                                  "Power was estimated before the run (python <script> --power).")
        print("wrote", p)
