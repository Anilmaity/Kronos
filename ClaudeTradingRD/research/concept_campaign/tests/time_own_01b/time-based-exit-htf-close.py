"""time-based-exit-htf-close — hold an opening-move trade to the 10:00 HTF candle close.

"the main TP final TP would be 10:00 a.m." (X4XSsv5CNqg); "you can hold this till 10:00
a.m." (U4j-fZD-FJk); "A 9:30-driven expansion is expected to terminate at 10:00, where the
4-hour, 1-hour and 30-minute candles all close"; "Take profit at the target if it is
reached before the boundary; the target takes precedence"; "After the boundary, treat the
day as finished". Contested concept; two readings, declared before the first run.

Common entry (the 9:30-driven expansion): the 15m candle opening at 09:30 NY. If it is an
expansion candle - body != 0 and opposing run (open -> extreme against the body) /
|body| <= 1.0 (threshold_fits small wick, grade A) - decide at its close (09:45), enter
the next M1 open in its direction, stop = its opposing extreme, target = the previous
trading day's high (long) / low (short) if not yet traded through this trading day
(18:00 roll, min_coverage 0.5), else no target.

Reading a (trade_test, claim '+'): the ride itself - exit at 10:00 NY (max_hold 15 min,
the close of the 30m/1h candle it runs inside) or the target/stop first; vs a matched
random entry at the same NY clock (+/-30 min).

Reading b (gate_test on a variant book, claim '+'): each entry appears twice - exit at
10:00 (gated) vs hold to 12:00 NY, the end of the NY a.m. session (complement; measurable
"P&L of exiting at 10:00 vs holding, on 9:30-driven expansions"). Same stop and target in
both. Control-adjusted R per row (controls share the hold), day-block CI pairs the two.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ny_mod, empty  # noqa: E402

CID = "time-based-exit-htf-close"
WICK_CUT = 1.0
HOLD_10 = pd.Timedelta("15min")
HOLD_12 = pd.Timedelta("135min")


def detect_a(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    b = cl.build_bars(m1, "15min")
    if len(b) < 10:
        return empty(cols)
    st = pd.DatetimeIndex(b.index)
    sel = np.flatnonzero(ny_mod(st) == 9 * 60 + 30)
    sel = sel[sel < len(b)]
    if len(sel) == 0:
        return empty(cols)
    o, h, l, c = (b[k].to_numpy(float)[sel] for k in ("open", "high", "low", "close"))
    body = c - o
    sgn = np.sign(body)
    opp = np.where(sgn > 0, o - l, h - o)
    ok = (sgn != 0) & (opp <= WICK_CUT * np.abs(body))
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[sel])
    sel, o, h, l, c, sgn, ct = sel[ok], o[ok], h[ok], l[ok], c[ok], sgn[ok], ct[ok]
    if len(sel) == 0:
        return empty(cols)
    pd_ = cl.prior_hilo(ct, "1D", m1=m1, min_coverage=0.5)
    run = cl.running_hilo(ct, "1D", m1=m1)
    pdh, pdl = pd_["high"].to_numpy(float), pd_["low"].to_numpy(float)
    rh, rl = run["high"].to_numpy(float), run["low"].to_numpy(float)
    tgt_l = np.where(np.isfinite(pdh) & np.isfinite(rh) & (rh < pdh) & (pdh > c), pdh, np.nan)
    tgt_s = np.where(np.isfinite(pdl) & np.isfinite(rl) & (rl > pdl) & (pdl < c), pdl, np.nan)
    out = pd.DataFrame({"decision_time": ct, "available_at": ct,
                        "direction": sgn.astype(int),
                        "stop_px": np.where(sgn > 0, l, h),
                        "target_px": np.where(sgn > 0, tgt_l, tgt_s)})
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


def detect_b(m1):
    a = detect_a(m1)
    if len(a) == 0:
        a["max_hold"] = pd.Series(dtype="timedelta64[ns]")
        a["exit_10"] = pd.Series(dtype=bool)
        return a
    x = a.assign(max_hold=HOLD_10, exit_10=True)
    y = a.assign(max_hold=HOLD_12, exit_10=False)
    out = pd.concat([x, y], ignore_index=True)
    return out.sort_values(["decision_time", "exit_10"], kind="stable").reset_index(drop=True)


def show(res):
    print({k: res.get(k) for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "verdict", "verdict_detail", "ties",
                                   "ctrl_overlap", "halves", "exposure_bars", "exit_mix",
                                   "sanity_flags")})


COMMON_RULES = [
    "the 15m candle opening 09:30 NY; expansion = body != 0 and opposing run / |body| <= 1.0",
    "decide at its close (09:45); enter next M1 open in its direction; stop = its opposing "
    "extreme; target = previous trading day's high/low (18:00 roll, min_coverage 0.5) if "
    "untaken and beyond the 09:45 close, else none"]
COMMON_SRC = {
    "wick_cut": "threshold_fits: small wick / expansion candle opposing_run/|body| <= 1.0 "
                "(grade A)",
    "entry_candle": "corpus: N3Ml-r0X30o 'it either ends at 10:00 or it can sometimes end "
                    "at 9:45'; a 9:30-driven expansion (detection rules)",
    "target": "corpus: execution targets 'the logical level (previous day low/high)'; "
              "'the target takes precedence'",
    "exit_10": "corpus: Je7cd9HJUBE 'time based is 10:00 a.m. because that's when we get "
               "new candles'",
    "ctrl_tod_tol_min": "declared-before-run: README trap 9, every entry at 09:45 NY"}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        ev = cl.cache_frame("tbe10_ride", lambda: detect_a(cl.load_m1()))
        print("a events", len(ev), "with target", int(ev["target_px"].notna().sum()))
        probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, max_hold="15min", claim="+", ctrl_tod_tol_min=30)
        show(res)
        op = {"rules": COMMON_RULES + ["exit at 10:00 NY (max_hold 15 min) unless stop/target "
                                       "first; control at the same NY clock +/-30 min"],
              "params": {"wick_cut": WICK_CUT, "entry_candle": "15m @ 09:30 NY",
                         "target": "untaken PDH/PDL", "exit_10": "15min",
                         "ctrl_tod_tol_min": 30}}
        print(cl.write_result(CID, "a", res, operationalization=op, params_source=COMMON_SRC,
                              script=__file__, probe=probe,
                              notes="Reading a: the 9:30 expansion ride held to the 10:00 "
                                    "boundary. Corpus context is index futures."))
    if "b" in which:
        ev = cl.cache_frame("tbe10_vs_12", lambda: detect_b(cl.load_m1()))
        print("b rows", len(ev), "gated", int(ev["exit_10"].sum()))
        probe = cl.probe_lookahead(detect_b, ev, lookback="10D")
        print("probe", probe.get("passed"))
        res = cl.gate_test(ev, "exit_10", mask_available_at="decision_time", claim="+",
                           ctrl_tod_tol_min=30)
        show(res)
        op = {"rules": COMMON_RULES + [
            "each entry twice: exit at 10:00 NY (15 min, gated) vs hold to 12:00 NY "
            "(135 min, complement); same stop/target; controls share each row's hold at "
            "the same NY clock +/-30 min"],
            "params": {"wick_cut": WICK_CUT, "entry_candle": "15m @ 09:30 NY",
                       "target": "untaken PDH/PDL", "exit_10": "15min",
                       "hold_alt": "135min (to 12:00)", "ctrl_tod_tol_min": 30}}
        src = dict(COMMON_SRC)
        src["hold_alt"] = ("session_window_fit: NY a.m. 08:30-12:00; corpus measurable "
                           "'give-back between the 10:00 close and the session close'")
        print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                              script=__file__, probe=probe,
                              notes="Reading b: variant book - the same 9:30-expansion "
                                    "entries exited at 10:00 vs held to 12:00. Rows are "
                                    "paired (same entry), so the day-block CI is the "
                                    "relevant component."))
