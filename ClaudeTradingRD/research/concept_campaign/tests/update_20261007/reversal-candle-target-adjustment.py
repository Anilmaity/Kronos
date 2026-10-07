"""reversal-candle-target-adjustment — update_20261007 new claims, RERUN with vault context.

Prior library readings a/b (model_own_02b) scored the reversal-day trade to the daily OPEN (a)
and to the day's opposing extreme (b): both NULL. They are untouched. Only the two NEW target
claims are scored here (u1007a / u1007b replace this script's own first pass of 2026-10-07).

Shared entry (bullish; bearish mirrors), identical to prior a/b, 1h execution:
  1h CISD (phase-3 locked: series_open, 2/2, max_wait 3), its extreme formed today and equal to
  today's running low at the confirm close, confirm close still BELOW the 18:00 NY daily open
  (opposing run in play). Decide at the confirming 1h close (close_time, never the label),
  enter the next M1 open, stop at the protected swing, flat 17:00 NY. One per day.

Reading u1007a (live_10, GRc5FVB5tdg): + reversal day (today's low below the previous day's
  low = expansion into a HTF target, then reversal); first such CISD per day (= prior reading
  a's events); target = PREVIOUS DAY'S EQ (wick-to-wick 50%), kept only if ahead. The rule by
  which wick size picks open vs EQ is unstated (draft ambiguity), so EQ is scored on every such
  day. Unchanged from the first pass.
Reading u1007b (edu_03, 3OIq9HmckH8): the LARGE-wick case only. Large = the opposing run did
  not respect the previous day's EQ ("if we had a small wick respecting the EQ, we could still
  get up to these highs"), i.e. today's low < PD EQ (bull). ADR(20) projected from the wick
  extreme: kept only if PDH is ahead and within it (PDH <= low + ADR), i.e. the projection
  reaches PDH -> PDH is the day's target, nothing beyond it (flat 17:00 NY). First per day.
  Change vs first pass: the first pass kept every day where PDH was reachable, small wicks
  included; the claim is about the large-wick case. The T-spot alternative is withheld at
  source (vault: TTrades Method Spec §9), so the EQ is the only computable reading.

Vault-driven settings (Backtest Methodology Traps; README §4 traps 7/9): the control holds the
NY clock (ctrl_tod_tol_min=30) because these events cluster in hours and every hold ends at
17:00 NY. All parameters declared before the first run of this script version.
"""
import importlib.util
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C          # model_own_02b helpers (same entry code as prior readings a/b)

_spec = importlib.util.spec_from_file_location(
    "risk_own_01b_common",
    "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b/_common.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)  # daily_ref / asof_ref (ADR as of the last closed day) / show

CID = "reversal-candle-target-adjustment"
ADR_DAYS = 20
TOD_TOL = 30
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]


def candidates(m1):
    """Every 1h CISD off today's running extreme, still beyond the 18:00 open."""
    d = C.daily(m1)
    dayo = C.window_stats(m1, "18:00", "17:00")
    h = C.complete_bars(m1, "1h")
    cz = C.cisd_table(h)
    if cz.empty:
        return cz
    td_h = cl.trading_day(h.index)
    run_lo = pd.Series(h["low"].to_numpy()).groupby(td_h).cummin().to_numpy()
    run_hi = pd.Series(h["high"].to_numpy()).groupby(td_h).cummax().to_numpy()
    ctn = pd.DatetimeIndex(h["close_time"]).as_unit("ns").asi8
    pos = np.searchsorted(ctn, pd.DatetimeIndex(cz["t"]).as_unit("ns").asi8)
    cz = cz.assign(td=cl.trading_day(cz["t"]), run_lo=run_lo[pos], run_hi=run_hi[pos])
    cz = cz[cl.trading_day(cz["extreme_start"]) == cz["td"]]
    pdx = C.prev_day_levels(d, cz["td"])
    cz["pdh"], cz["pdl"] = pdx["pdh"].to_numpy(), pdx["pdl"].to_numpy()
    cz["pdeq"] = (cz["pdh"] + cz["pdl"]) / 2
    cz["dopen"] = dayo["o"].reindex(cz["td"]).to_numpy()
    bull = ((cz["dir"] == 1) & np.isclose(cz["extreme_price"], cz["run_lo"])
            & (cz["confirm_close"] < cz["dopen"]))
    bear = ((cz["dir"] == -1) & np.isclose(cz["extreme_price"], cz["run_hi"])
            & (cz["confirm_close"] > cz["dopen"]))
    cz = cz[(bull | bear).to_numpy()].copy()
    cz["wick_x"] = np.where(cz["dir"] == 1, cz["run_lo"], cz["run_hi"])
    return cz.sort_values("t", kind="stable").reset_index(drop=True)


def _frame(q, target):
    t = pd.DatetimeIndex(q["t"])
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": q["dir"].astype(int).to_numpy(),
                        "stop_px": q["stop"].to_numpy(float),
                        "target_px": np.asarray(target, float),
                        "max_hold": C.session_end(t) - t})
    return out[out["max_hold"] > pd.Timedelta(0)].reset_index(drop=True)


def detect_a(m1):
    cz = candidates(m1)
    if cz.empty:
        return pd.DataFrame(columns=COLS)
    s = cz["dir"].to_numpy()
    key = np.where(s == 1, cz["run_lo"] < cz["pdl"], cz["run_hi"] > cz["pdh"])
    q = cz[key].groupby("td", sort=True).head(1)            # = prior reading a's event set
    eq = q["pdeq"].to_numpy(float)
    ahead = q["dir"].to_numpy() * (eq - q["confirm_close"].to_numpy(float)) > 0
    return _frame(q[ahead], eq[ahead])


def detect_b(m1):
    cz = candidates(m1)
    if cz.empty:
        return pd.DataFrame(columns=COLS)
    adr = R.asof_ref(R.daily_ref(m1, ADR_DAYS, C.MIN_DAY_M1), cz["t"])["adr"].to_numpy(float)
    s = cz["dir"].to_numpy()
    P = cz["confirm_close"].to_numpy(float)
    wx = cz["wick_x"].to_numpy(float)
    tgt = np.where(s == 1, cz["pdh"], cz["pdl"]).astype(float)
    proj = wx + s * adr                                     # ADR from the wick extreme
    with np.errstate(invalid="ignore"):
        large = s * (cz["pdeq"].to_numpy(float) - wx) > 0   # wick did not respect PD EQ
        keep = (np.isfinite(adr) & np.isfinite(tgt) & large
                & (s * (tgt - P) > 0) & (s * (proj - tgt) >= 0))
    q = cz[keep].assign(tgt=tgt[keep]).groupby("td", sort=True).head(1)
    return _frame(q, q["tgt"].to_numpy(float))


BASE_RULES = [
    "1h CISD (series_open, 2/2, max_wait 3), extreme formed today = today's running low "
    "(bull) / high (bear) at the confirm close, confirm close still beyond the 18:00 NY open "
    "(opposing run in play); decide at the 1h close_time, enter next M1 open, stop at the "
    "protected swing, flat 17:00 NY",
    "control holds the NY clock (+/-30 min) so its hold window and time-of-day volatility "
    "match the real trade"]
PARAMS = {"exec_tf": "1h", "cisd": "series_open, swing 2/2, max_wait 3",
          "reversal_candle": "confirm close still beyond the 18:00 open (opposing run in play)",
          "daily_open": "18:00 NY", "exit": "17:00 NY session close", "one_per_day": True,
          "prev_day": "last complete trading day with n_m1 >= 600", "grid4h": "n/a",
          "ctrl_tod_tol_min": TOD_TOL}
SRC = {"exec_tf": "method_spec: §2.4 daily wick confirmed by an hourly CISD (as prior a/b)",
       "cisd": "phase3: locked CISD config",
       "reversal_candle": "threshold_fits: large wick = opposing_run/|body| > 1.0; live proxy "
                          "as prior reading a/b (declared-before-run)",
       "daily_open": "method_spec: §1.4 daily open 18:00 canon",
       "exit": "corpus: 3OIq9HmckH8 'better to wait for the new candle or the new daily open'",
       "one_per_day": "method_spec: §2.4 only one CISD per day",
       "prev_day": "declared-before-run: README trap 6, skip stub sessions",
       "grid4h": "declared-before-run: no 4h bars used",
       "ctrl_tod_tol_min": "declared-before-run: README trap 9 + vault Backtest Methodology "
                           "Traps / Session Timing on Gold - events cluster in NY hours and "
                           "every hold ends at 17:00 NY, so the control holds the clock"}


def tod_profile(ev):
    """NY-hour share of events, in 4h blocks from the 18:00 roll (detector output only)."""
    h = (cl.ny_minute_of_day(ev["decision_time"]) // 60 - 18) % 24
    return (pd.Series(h // 4).value_counts(normalize=True).sort_index().round(3)
            .rename(lambda b: f"{(18 + 4 * b) % 24:02d}-{(22 + 4 * b) % 24:02d}").to_dict())


def run(reading, detect, key, rules, params, src, notes, dry=False):
    ev = cl.cache_frame(key, lambda: detect(cl.load_m1()))
    m1 = cl.load_m1()
    entry = m1["open"].reindex(pd.DatetimeIndex(ev["decision_time"]), method="bfill").to_numpy()
    sd = np.abs(entry - ev["stop_px"].to_numpy(float))
    print(reading, "rows", len(ev), ev["direction"].value_counts().to_dict(),
          "stop pt median", np.nanmedian(sd).round(2), "p10", np.nanpercentile(sd, 10).round(2))
    print("  tod (NY 4h blocks from 18:00)", tod_profile(ev))
    if dry:
        return
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=None, claim="+", ctrl_tod_tol_min=TOD_TOL)
    R.show(res)
    print(cl.write_result(CID, reading, res,
                          operationalization={"rules": BASE_RULES + rules,
                                              "params": {**PARAMS, **params}},
                          params_source={**SRC, **src}, script=__file__, probe=probe,
                          notes=notes))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    dry = "--dry" in sys.argv
    if "a" in which:
        run("u1007a", detect_a, "rcta_u1007a_prev_eq_v1",
            ["reversal day: today's extreme beyond the previous day's low (bull) / high (bear); "
             "first such CISD per day (= prior reading a's events)",
             "target = previous day's EQ (PDH+PDL)/2, kept only if ahead of the confirm close"],
            {"key_level": "previous day low/high taken by today's extreme",
             "target": "previous complete day's wick-to-wick 50% (EQ)",
             "eq": "whole-candle wick-to-wick 50%"},
            {"key_level": "corpus: reversal-candle-target-adjustment precondition 'The day's "
                          "extreme formed from a key level' (as prior a/b)",
             "target": "corpus: GRc5FVB5tdg 'your targets back towards the daily open to the "
                       "previous EQ'",
             "eq": "corpus: GRc5FVB5tdg 'already hit the previous EQ'; equilibrium-eq a/b "
                   "wick-to-wick 50% (declared-before-run)"},
            "Rerun with vault context. New named target only (previous-day EQ). The wick-size "
            "rule choosing open vs EQ is unstated in the source, so EQ is scored on every "
            "reversal day where it is ahead; the open target is prior reading a (NULL). Source "
            "stream is index futures, discretionary. Control holds the NY clock (README trap 9).",
            dry)
    if "b" in which:
        run("u1007b", detect_b, "rcta_u1007b_adr_largewick_pdx_v2",
            ["large opposing wick: today's running low (bull) is below the previous day's EQ "
             "(the wick did not respect the EQ); bear mirrors",
             "ADR = mean H-L of the last 20 complete real days (n_m1 >= 600), as of the "
             "decision (in-progress day never read)",
             "projection = wick extreme (today's low so far, bull) + ADR (minus for bear)",
             "kept only if PDH (bull) / PDL (bear) is ahead of the confirm close and within the "
             "projection (PDH <= wick_low + ADR); first such CISD per day",
             "target = PDH (bull) / PDL (bear); no trade beyond it (flat at 17:00 NY)"],
            {"large_wick": "wick extreme beyond the previous complete day's EQ (PDH+PDL)/2",
             "adr": "ADR(20) mean of H-L, completed real days",
             "projection_anchor": "today's running extreme at the confirm close (the CISD extreme)",
             "reach_rule": "target within wick_extreme +/- ADR (no tolerance band)",
             "target": "previous complete day's high (long) / low (short)"},
            {"large_wick": "corpus: 3OIq9HmckH8 'if we had a small wick respecting the EQ, we "
                           "could still get up to these highs' (T-spot alternative withheld "
                           "at source; declared-before-run)",
             "adr": "corpus: 3OIq9HmckH8 'total range divided by the total days' / 'Ideally, "
                    "you use a few more' - length unstated; 20 as average-daily-range__a "
                    "(declared-before-run)",
             "projection_anchor": "corpus: 3OIq9HmckH8 'If this is the high, where does our "
                                  "115 lie? Right at this previous day's low'",
             "reach_rule": "corpus: 3OIq9HmckH8 'when we have a large opposing move, this is "
                           "using time and range'; 'at/near' tolerance unstated -> plain "
                           "reachability (declared-before-run)",
             "target": "corpus: 3OIq9HmckH8 'we have our previous day's high here ... this is "
                       "our target now'"},
            "Rerun with vault context. Scores the large-wick case of the ADR-from-wick-extreme "
            "rule: wick beyond the PD EQ, projection reaches PDH/PDL, which is the target. The "
            "first pass also kept small-wick days. The 'farther target' it replaces (open "
            "targets, failure swings) is discretionary and not modelled. The no-continuation-"
            "beyond-PDH/PDL half is the pdh-pdl-continuation-adr-gate concept and is not scored "
            "here. Vault: PDH/PDL are reached slightly less often than an equidistant level "
            "(previous-period-high-low). Control holds the NY clock (README trap 9).",
            dry)
