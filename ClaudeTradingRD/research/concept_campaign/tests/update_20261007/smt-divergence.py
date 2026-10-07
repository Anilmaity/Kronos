"""smt-divergence -- update 2026-10-07 (TTrades live_03 / live_11 / edu_01 drafts).

New claims vs the library entry (prior readings a/b = bare hourly swing SMT, NULL):
  live_03: a STRUCTURAL SMT at a range extreme / previous-day level (silver runs out the
           low, gold does not -> gold, closer to the highs, is the long toward the range
           high), confirmed by a change in the state of delivery (CISD). rVRk4MLTJSs.
  live_11: 3m gold/silver SMT and 1m SMT are not used to frame an idea. KBJAGgkXdeI.
  edu_01 : multiple SMTs on different timeframes can stack on one leg. yH4eYwUgdTY.

u1007a (trade_test, claim '+'): phase-3 1h gold CISD, kept only when a structural
  previous-day SMT printed in the same trading day by the confirm bar, with gold the HOLDER:
  bullish = silver traded below its prior-day low, gold did not trade below its own;
  bearish mirror at prior-day highs. Trade gold in the CISD direction, stop = protected
  swing, target = gold's opposite prior-day extreme ("long toward the range high").
u1007b: UNTESTABLE -- the 1m/3m-vs-higher SMT timeframe floor and multi-TF stacking need
  sub-hourly silver; the campaign's correlate holdings are XAG H1/D1 only.

AUDIT 2026-10-07 (vault context): detect() unchanged. Fixed (a) the u1007a control did not
  hold the NY clock although the events cluster by hour (TV distance 0.163 vs all 1h
  closes; 19-20 NY closes at 0.09-0.13x) -> ctrl_tod_tol_min=30 per README trap 9, as the
  2026-09-23 readings a/b declared; (b) the u1007b reason read a file's extent (the 2024-12
  M15 file) as a data limit (vault trap 7) -> restated as a holdings limit.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402

import concept_lab as cl                 # noqa: E402
from detectors.cisd import cisd_events   # noqa: E402

CID = "smt-divergence"
XAG_PATH = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet"
HOLD = "10h"
OHLC = ["open", "high", "low", "close"]
_XAG = None


def xag_for(m1):
    global _XAG
    if _XAG is None:
        x = pd.read_parquet(XAG_PATH)
        if "time" in x.columns:
            x = x.set_index("time")
        x.index = pd.to_datetime(x.index, utc=True)
        x = x[OHLC].astype(float).sort_index()
        _XAG = x[~x.index.duplicated(keep="first")]
    end = pd.DatetimeIndex(m1.index).max() + pd.Timedelta(minutes=1)
    start = pd.DatetimeIndex(m1.index).min().floor("1h")
    return _XAG[(_XAG.index >= start) & (_XAG.index + pd.Timedelta(hours=1) <= end)]


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    b = cl.build_bars(m1, "1h")
    if len(b) < 50:
        return pd.DataFrame(columns=cols)
    ev = cisd_events(b[OHLC], level_rule="series_open", left=2, right=2,
                     max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    y = xag_for(m1).reindex(b.index)          # silver on gold's 1h grid (NaN if missing)
    td = cl.trading_day(b.index)
    f = pd.DataFrame({"td": td, "gh": b["high"].to_numpy(), "gl": b["low"].to_numpy(),
                      "sh": y["high"].to_numpy(), "sl": y["low"].to_numpy()}, index=b.index)
    days = f.groupby("td")[["gh", "gl", "sh", "sl"]].agg(
        {"gh": "max", "gl": "min", "sh": "max", "sl": "min"})
    prev = days.shift(1)                      # previous trading day present in the data
    # first day in the slice has no prior day in the slice -> NaN (no event)
    p = prev.reindex(f["td"]).to_numpy()
    pgh, pgl, psh, psl = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
    g = f.groupby("td")
    run_gl = g["gl"].cummin().to_numpy()
    run_gh = g["gh"].cummax().to_numpy()
    run_sl = g["sl"].transform(lambda s: s.cummin().ffill()).to_numpy()
    run_sh = g["sh"].transform(lambda s: s.cummax().ffill()).to_numpy()
    first_day = f["td"].to_numpy() == f["td"].iloc[0]

    pos = pd.Series(np.arange(len(b)), index=b.index)
    c = pos.loc[ev["confirm_time"]].to_numpy()
    bull = (ev["direction"] == "bullish").to_numpy()
    with np.errstate(invalid="ignore"):
        smt_bull = (run_sl[c] < psl[c]) & (run_gl[c] >= pgl[c])
        smt_bear = (run_sh[c] > psh[c]) & (run_gh[c] <= pgh[c])
    smt = np.where(bull, smt_bull, smt_bear) & ~first_day[c]
    tgt = np.where(bull, pgh[c], pgl[c])
    cc = b["close"].to_numpy()[c]
    stop = ev["protected_swing"].to_numpy(float)
    ok = smt & np.isfinite(tgt) & np.where(bull, (tgt > cc) & (stop < cc), (tgt < cc) & (stop > cc))
    dt = pd.DatetimeIndex(b["close_time"].to_numpy()[c])
    out = pd.DataFrame({"decision_time": dt, "available_at": dt,
                        "direction": np.where(bull, 1, -1), "stop_px": stop,
                        "target_px": tgt})[ok]
    out = out.drop_duplicates(subset=["decision_time", "direction"])
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    ev = cl.cache_frame("smt_u1007a_structural_pd_cisd_v1", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=HOLD, claim="+", ctrl_tod_tol_min=30)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "exposure_bars", "ctrl_overlap"):
        print(" ", k, res.get(k))
    rules = [
        "pair: gold 1h (traded) vs silver XAG_USD H1 (OANDA) on gold's bar starts; only silver "
        "bars closed by the slice end are read",
        "model: phase-3 1h gold CISD (series_open level, 2/2 swing, max_wait 3, min_series 1); "
        "decide at confirm-bar close, enter next M1 open",
        "structural SMT (previous-day level, 18:00 NY roll): bullish = from the trading-day "
        "start through the confirm bar silver traded below its prior-day low while gold stayed "
        ">= its own prior-day low; bearish mirror at prior-day highs",
        "keep only CISDs whose direction matches a structural SMT in the same trading day "
        "(SMT confirmed by the change in state of delivery); gold = the holder (strongest)",
        "stop = CISD protected swing; target = gold's opposite prior-day extreme (PDH long / "
        "PDL short); drop if the confirm close is already beyond target or stop; 10h hold",
        "control: matched random entries (direction, stop/target distance, +-30 days) held "
        "within +-30 min of the event's NY clock time (events cluster by hour)",
        "untested here: 'readable before the model closes' (timing nuance, no measurable "
        "contrast on H1), the counter-trend-short filter, the 1m/3m floor and MTF stacking"]
    params = {"tf": "1h", "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
              "min_series": 1, "max_hold": HOLD, "correlate": "XAG_USD H1",
              "range_level": "previous trading day high/low", "day_open_hour": 18,
              "target": "opposite prior-day extreme", "stop": "protected swing",
              "ctrl_tod_tol_min": 30}
    P3 = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked config)"
    src = {"tf": P3 + "; correlate held at H1 only", "level_rule": P3, "swing": P3,
           "max_wait": P3, "min_series": P3, "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "stop": P3,
           "correlate": "corpus: rVRk4MLTJSs 'I was using silver for this. Yeah, silver ran out "
                        "the low. Gold didn't.'",
           "range_level": "corpus: rVRk4MLTJSs 'there is no SMT there between previous day low "
                          "on this. This is like a structural SMT.'",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9, SMT is not a timing concept "
                               "but these events cluster by NY hour (TV distance 0.163 vs all 1h "
                               "closes, measured on the event frame before the audit re-run); same "
                               "declaration as smt-divergence readings a/b",
           "target": "corpus: rVRk4MLTJSs 'Gold is closer to these highs. So, it makes more "
                     "sense to be longing gold ... Gold pushes through this high'"}
    p = cl.write_result(CID, "u1007a", res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Tests live_03's structural (previous-day) SMT + CISD confirmation "
                              "with the traded asset as the holder. Hourly only. Distinct from "
                              "smt-divergence-confluence__a (gold the SWEEPER at PDH/PDL). AUDIT "
                              "2026-10-07: control now held at the NY clock (ctrl_tod_tol_min=30).")
    print("wrote", p)
    reason = ("needs sub-hourly correlated-asset data: the 1m/3m SMT timeframe floor (live_11) "
              "and multi-timeframe SMT stacking (edu_01) compare 1m/3m/5m+ gold/silver SMTs; "
              "the campaign's correlate holdings are XAG_USD H1/D1 (OANDA, 2010-01-03 on). The "
              "only sub-hourly silver on disk (market_structure cont_xag_M15, 2024-12-30 on) is a "
              "fetch extent, not a source limit, and cannot fill the H1/H2 split; fetching "
              "sub-hourly silver is outside a tester's remit")
    p2 = cl.write_untestable(CID, reason, reading="u1007b", script=__file__,
                             notes="live_11 KBJAGgkXdeI 'I don't really like to trust the three "
                                   "minute SMT with silver'; edu_01 yH4eYwUgdTY 'multiple SMTs "
                                   "across multiple different time frames'.")
    print("wrote", p2)


if __name__ == "__main__":
    main()
