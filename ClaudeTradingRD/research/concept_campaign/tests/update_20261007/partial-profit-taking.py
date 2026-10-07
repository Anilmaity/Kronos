"""partial-profit-taking — update u1007 (TTrades, uW55Tuk-ngY): ADR-reached / correlated-asset partials.

Source: "it can definitely chop, right? Because ... we're already at our daily range. That's the
whole reason I took a partial right here and because if you look ES already took out this low,
but technically we have a divergence here. ... I partial a small part of my position. My main
position is to hold this for longer." / "The reason I took profit ... is cuz what? ES took out my
target, right? Which is TP."

u1007a (ADR trigger): the partial is justified iff, once the day has printed its average daily
range, further travel in the direction of the day's expansion is worse than usual. Event = the
first M1 bar of the trading day whose running high-low reaches ADR; direction = the side that
bar extended (new day high -> +1, new day low -> -1), i.e. the held position's side. Symmetric
bracket of 0.25*ADR either way, 4h hold. claim '-': continuing in the expansion direction after
ADR is worse than a matched random same-direction entry (=> taking the partial is right).

u1007b (correlated-asset trigger): gold traded, silver (XAG_USD H1) as the correlated asset, the
target = each asset's previous-day high/low. Silver tags its PDH/PDL while gold has not taken its
own -> the partial says gold's move is done. This is the gold/silver form already built and run
on 2026-09-23 as cross-asset-target-transfer reading b; its detector is reused UNCHANGED (same
frame) so this reading is the same hypothesis, not a new fork.

AUDIT 2026-10-07 (vault context) — fixes against the first u1007 version of this script:
 1. u1007a control was not time-of-day matched. ADR-reached events cluster in the London/NY
    hours (README trap 9; vault Session Timing on Gold). The own-voice concept making the same
    claim (average-daily-range a/b, 2026-09-23) was a raw EDGE refuted by verification as
    exactly this confound ("ToD-matched control gives NULL"); the guest form with the same
    event (adr-remaining-filter b) was run ToD-matched. -> ctrl_tod_tol_min=30.
 2. u1007a ADR lookback 14 was a generic-ICT default ("common ADR default"), not the source.
    The channel's own ADR concept gives only 'lately' / 'this month'; the campaign's own-voice
    ADR object is ADR(20) mean of H-L over real days (n_m1 >= 600), average-daily-range a.
    -> reuse that exact object (risk_own_01b/_common.daily_ref).
 3. u1007b was written UNTESTABLE as "the harness has XAUUSD M1 only". False: silver H1
    2010->2026 (m3_scalper/xag_h1_full.parquet) is the campaign's SMT correlate and this very
    trigger was tested on it (vault trap 7: never infer a data limit). -> tested on the 09-23
    frame, ToD-matched control by the same trap-9 rule if its events cluster in hours.
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TESTS = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests")


def _load(name, path):
    # the two precedent batches each ship a module called `_common`; load them under own names
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


catt = _load("ppt_catt", TESTS / "structure_own_04b" / "cross-asset-target-transfer.py")
adrc = _load("ppt_adr_common", TESTS / "risk_own_01b" / "_common.py")

CID = "partial-profit-taking"
ADR_N = 20          # = average-daily-range a (own voice): ADR(20) mean H-L over real days
MIN_N_M1 = 600      # real day = >= 600 M1 bars (same object as average-daily-range a)
BRACKET = 0.25      # stop = target = 0.25 * ADR
HOLD = "4h"
TOD = 30            # control matched on NY time of day +/- 30 min (README trap 9)


def detect(m1):
    """u1007a: first M1 close of each trading day at which the running day range >= ADR(20)."""
    td = cl.trading_day(m1.index).to_numpy()
    hi = pd.Series(m1["high"].to_numpy()).groupby(td).cummax().to_numpy()
    lo = pd.Series(m1["low"].to_numpy()).groupby(td).cummin().to_numpy()
    # ADR as of each trading day's first bar: completed real days only (asof close_time <= t)
    day_first = pd.Series(m1.index).groupby(td).first()
    ref = adrc.daily_ref(m1, ADR_N, MIN_N_M1)
    a_day = adrc.asof_ref(ref, pd.DatetimeIndex(day_first.to_numpy()))["adr"].to_numpy(float)
    a = pd.Series(a_day, index=day_first.index).reindex(td).to_numpy()
    hit = np.isfinite(a) & ((hi - lo) >= a)
    first = hit & (pd.Series(hit.astype(int)).groupby(td).cumsum().to_numpy() == 1)
    idx = np.flatnonzero(first)
    up = m1["high"].to_numpy()[idx] >= hi[idx]
    dn = m1["low"].to_numpy()[idx] <= lo[idx]
    d = np.where(up & ~dn, 1, np.where(dn & ~up, -1, 0))
    keep = d != 0     # both extremes in the triggering bar -> ambiguous side, dropped
    t = (m1.index[idx] + pd.Timedelta("1min"))[keep]          # the bar's close (label="left")
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": d[keep],
                         "stop_dist": BRACKET * a[idx][keep],
                         "target_dist": BRACKET * a[idx][keep]}).reset_index(drop=True)


detect_b = catt.detect_b      # u1007b: the 09-23 cross-asset-target-transfer reading-b frame


def ny_hour_share(ev):
    """Share of events in the busiest 4 NY hours (clock share of 4 hours = 4/23 = 17.4%)."""
    h = cl.to_ny(pd.DatetimeIndex(ev["decision_time"])).hour
    return float(pd.Series(h).value_counts(normalize=True).nlargest(4).sum())


def frames():
    ev_a = cl.cache_frame(f"ppt_adr{ADR_N}_n{MIN_N_M1}_first_hit_b{BRACKET}",
                          lambda: detect(cl.load_m1()))
    ev_b = cl.cache_frame("ppt_catt_b_1h_1.0_1.0", lambda: detect_b(cl.load_m1()))
    return ev_a, ev_b


def show(res):
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                                    "verdict_detail", "ties", "ctrl_overlap", "exposure_bars",
                                    "exit_mix")})


if __name__ == "__main__":
    ev_a, ev_b = frames()
    for name, ev in (("u1007a", ev_a), ("u1007b", ev_b)):
        print(name, "events", len(ev), ev.direction.value_counts().to_dict(),
              "top-4 NY-hour share", round(ny_hour_share(ev), 3))

    # ---- u1007a: ADR-reached partial ------------------------------------------------------
    probe = cl.probe_lookahead(detect, ev_a, lookback="60D")
    res = cl.trade_test(ev_a, max_hold=HOLD, claim="-", ctrl_tod_tol_min=TOD)
    show(res)
    op = {"rules": [
        "ADR = mean high-low of the last 20 real trading days (18:00 NY roll, n_m1 >= 600), "
        "as of the last completed day (risk_own_01b daily_ref, = average-daily-range a)",
        "event = first M1 bar of the trading day at which the running day range >= ADR; decide at "
        "that bar's close; direction = side that bar extended (new day high long, new day low "
        "short; bars making both dropped) = the side of the position being partialled",
        "held leg modelled as a fresh entry next M1 open, stop = target = 0.25*ADR, exit by 4h",
        "control: matched random same-direction entries, +/-30 d, NY time of day +/-30 min",
        "claim '-': continuation in the expansion direction after the ADR prints is worse than a "
        "matched random same-direction entry (=> the partial at ADR is warranted)"],
        "params": {"adr_n": ADR_N, "min_n_m1": MIN_N_M1, "bracket_adr": BRACKET,
                   "max_hold": HOLD, "day_open_hour": 18, "ctrl_tod_tol_min": TOD}}
    src = {"adr_n": "corpus: concepts/risk/average-daily-range.yaml (own voice) gives no lookback, "
                    "only 'lately' / 'this month' -> ~20 trading days; the campaign's own-voice ADR "
                    "object average-daily-range a (ADR20 mean H-L) reused unchanged (declared-before-run)",
           "min_n_m1": "declared-before-run: days with < 600 M1 bars are data-hole stubs (README "
                       "trap 6), as in average-daily-range a",
           "bracket_adr": "declared-before-run: no stop/target given for the held leg; symmetric "
                          "quarter-ADR bracket = the stop of adr-remaining-filter b (same event)",
           "max_hold": "declared-before-run: 'it can definitely chop' — rest of the session, capped "
                       "4h, as adr-remaining-filter b",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9 — ADR-reached events cluster in "
                               "NY hours; average-daily-range a/b EDGE was refuted by verification "
                               "as a time-of-day confound (NULL once ToD-matched)"}
    p = cl.write_result(CID, "u1007a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="AUDIT 2026-10-07: rerun with a ToD-matched control and the campaign's "
                              "own-voice ADR(20). Same hypothesis family as average-daily-range a/b "
                              "(refuted EDGE, ToD confound) and adr-remaining-filter b (same event "
                              "faded, ToD-matched, NULL): a replication, not independent evidence. "
                              "Partial size ('a small part') does not affect the sign of the test.")
    print("wrote", p)

    # ---- u1007b: correlated-asset partial (gold/silver) -----------------------------------
    probe_b = cl.probe_lookahead(detect_b, ev_b, lookback="20D")
    res_b = cl.trade_test(ev_b, max_hold="10h", claim="+", ctrl_tod_tol_min=TOD)
    show(res_b)
    op_b = {"rules": [
        "traded asset gold; correlated asset silver (XAG_USD H1 joined on gold's 1h labels)",
        "target = each asset's own previous trading-day high/low (18:00 NY roll)",
        "event = silver's first 1h bar of the trading day whose high reaches silver's PDH (low "
        "reaches PDL) while gold has NOT taken its own PDH (PDL) through that bar; decide at the "
        "bar's close (detector = cross-asset-target-transfer reading b, 2026-09-23, unchanged)",
        "the partial says gold's move is done: trade gold against the move (short at a high tag, "
        "long at a low tag), next M1 open, stop 1.0 x ATR14(gold 1h), target 1R, 10h",
        "control: matched random same-direction entries, +/-30 d, NY time of day +/-30 min",
        "claim '+': gold turns more than at a matched random moment (=> the partial is warranted)"],
        "params": {"tf": "1h", "level": "PDH/PDL per asset", "correlate": "XAG_USD H1",
                   "min_coverage": 0.5, "stop_atr": 1.0, "rr": 1.0, "max_hold": "10h",
                   "ctrl_tod_tol_min": TOD}}
    src_b = {"tf": "phase3: 1h rung-0 timeframe; silver correlate exists only at H1",
             "level": "corpus: uW55Tuk-ngY 'ES took out my target, right? Which is TP.' / 'ES "
                      "already took out this low' — the target is the correlated asset's level; "
                      "previous-day high/low as in cross-asset-target-transfer b (method_spec §2.7)",
             "correlate": "phase3 correlate file XAG_USD H1 (gold's correlated metal), as "
                          "cross-asset-target-transfer b",
             "min_coverage": "declared-before-run: skip stub sessions for gold PDH/PDL (README trap 6)",
             "stop_atr": "declared-before-run (2026-09-23, cross-asset-target-transfer b): symmetric "
                         "1.0 x ATR14(gold 1h) barrier; the source gives no distance",
             "rr": "declared-before-run (2026-09-23, cross-asset-target-transfer b): 1R turn test",
             "max_hold": "phase3: 10 entry-TF periods (1h)",
             "ctrl_tod_tol_min": "declared-before-run: README trap 9 — PDH/PDL tags cluster in "
                                 "NY hours; same control as u1007a"}
    p2 = cl.write_result(CID, "u1007b", res_b, operationalization=op_b, params_source=src_b,
                         script=__file__, probe=probe_b,
                         notes="AUDIT 2026-10-07: was UNTESTABLE ('XAUUSD M1 only'), which is false — "
                               "silver H1 is the campaign's correlate. Same hypothesis and frame as "
                               "cross-asset-target-transfer b (2026-09-23, NULL -0.053R, unmatched "
                               "ToD); re-scored here with a ToD-matched control — a replication, "
                               "not independent evidence. Gold/silver stands in for ES/NQ.")
    print("wrote", p2)
