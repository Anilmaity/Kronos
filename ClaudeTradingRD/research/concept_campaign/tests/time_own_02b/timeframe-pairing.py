"""timeframe-pairing (contested, own voice). Pair worked in the unit: 1H context -> 5m entry
(lvM278EeQlw, XwL3Hy9za7M). Baseline = phase-3 bare 5m CISD book (hold 50 min = 10 entry-TF
periods), gate tests, claim '+'.

reading a -- ALIGNMENT is the trigger: 'Require the LTF setup direction to match the HTF
    structure direction' / 'a 5-minute bearish setup that aligns with the hourly bearish
    structure'. HTF structure direction = direction of the most recent 1h CISD confirmed at or
    before the 5m decision (the corpus's own change-in-state-of-delivery on the paired TF;
    same phase-3 CISD config). gated = same direction. Events with no prior 1h CISD dropped.
reading b -- the POI clause: 'Only drop to the execution timeframe once price has reached a
    level on the paired higher timeframe'. Level = the prior completed 1h bar's low (for a
    bullish 5m CISD) / high (bearish), read as of 60 min before the decision; gated = price
    traded through that level within the 60 minutes up to the decision (the last 12 completed
    5m bars). Everything is read from bars closed by the decision.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params, base_rule, summarize

READING = sys.argv[1] if len(sys.argv) > 1 else "a"
TF = "5min"


def detect(m1):
    ev = cisd_book(m1, TF)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    d = ev["direction"].to_numpy()
    if READING == "a":
        h = cisd_book(m1, "1h")
        a = cl.asof(h, t, avail_col="decision_time")
        hd = a["direction"].to_numpy(float)
        ok = np.isfinite(hd)
        ev["gated"] = np.where(ok, hd == d, False)
        ev["mask_at"] = pd.DatetimeIndex(a["available_at"]).tz_convert("UTC")
        ev = ev[ok].reset_index(drop=True)
        ev["mask_at"] = pd.DatetimeIndex(ev["mask_at"])
        return ev
    b5 = cl.build_bars(m1, "5min")
    lo12 = b5["low"].rolling(12, min_periods=12).min()
    hi12 = b5["high"].rolling(12, min_periods=12).max()
    w = pd.DataFrame({"close_time": b5["close_time"].to_numpy(), "lo12": lo12.to_numpy(),
                      "hi12": hi12.to_numpy(),
                      "start12": b5["close_time"].shift(11).to_numpy()}, index=b5.index)
    # 12 consecutive 5m bars must span exactly 60 min (no halt/gap inside the window)
    w["contig"] = (pd.DatetimeIndex(w["close_time"]) - pd.DatetimeIndex(w["start12"])) == pd.Timedelta("55min")
    a = cl.asof(w, t)
    t0 = t - pd.Timedelta("60min")
    ph = cl.prior_hilo(t0, "1h", m1=m1)
    lvl_lo, lvl_hi = ph["low"].to_numpy(float), ph["high"].to_numpy(float)
    ok = np.isfinite(lvl_lo) & np.isfinite(a["lo12"].to_numpy(float)) & a["contig"].fillna(False).to_numpy(bool) \
        & (pd.DatetimeIndex(a["available_at"]).tz_convert("UTC") == t)
    reached = np.where(d == 1, a["lo12"].to_numpy(float) < lvl_lo, a["hi12"].to_numpy(float) > lvl_hi)
    ev["gated"] = np.where(ok, reached, False)
    ev = ev[ok].reset_index(drop=True)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"to02b_tfpair_{READING}_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), "events; gated share", ev["gated"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    mat = "mask_at" if READING == "a" else "decision_time"
    res = cl.gate_test(ev, "gated", mask_available_at=mat, max_hold="50min", claim="+")
    summarize(res)
    bp, bs = base_params(TF)
    if READING == "a":
        params = {**bp, "htf": "1h", "htf_direction": "most recent 1h CISD (phase-3 config) confirmed at/before the decision"}
        src = {**bs, "htf": "corpus: lvM278EeQlw 'a 5-minute bearish setup that aligns with the hourly bearish structure'",
               "htf_direction": "declared-before-run: HTF structure direction = latest change in state of delivery on the paired TF (phase-3 CISD)"}
        rules = [base_rule(TF), "gated = 5m CISD direction equals the most recent confirmed 1h CISD direction; complement = opposite",
                 "events with no prior 1h CISD dropped"]
    else:
        params = {**bp, "htf": "1h", "poi_level": "prior completed 1h bar low (longs) / high (shorts), as of decision-60min",
                  "reach_window": "last 12 completed 5m bars (60 min), contiguous"}
        src = {**bs, "htf": "corpus: pair table 1H->5m (lvM278EeQlw, AdmnWLjf8rY)",
               "poi_level": "declared-before-run: 'Only drop to the execution timeframe once price has reached a level on the paired higher timeframe' (hh_kKK4Fhrw); HTF old high/low as the level",
               "reach_window": "declared-before-run: one paired-HTF period"}
        rules = [base_rule(TF), "gated = within the 60 min up to the decision price traded through the prior 1h bar's low (longs) / high (shorts)",
                 "complement = 5m CISD with no such HTF level reached"]
    p = cl.write_result("timeframe-pairing", READING, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Pair 1H->5m from the worked Shorts examples; the full three-rung ladders are the phase-3 conjunction (already refuted) and are not re-run here.")
    print(p)
