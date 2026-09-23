"""weekly-profile-framework (model, TTrades own voice, contested).

Reading a (trade_test): the framework's trade. A daily candle-2 closure that is the week's
extreme so far (bullish: swept the prior day's low, closed back above it, and its low is the
lowest low of the week to date; bearish mirror), confirmed by an hourly CISD inside that daily
candle whose extreme IS the daily wick extreme -> trade the next day (candle 3) away from the
extreme: enter at the next session open (decision = the daily close), stop at the confirmed
extreme, target 2R, flat after one session.

Reading b (gate_test): the framework's confirmation gate. Baseline = every daily C2 at the
week's extreme traded the same way; gate = the hourly CISD confirmation is present
(measurable: "hit rate of candle 3 continuing ... conditioned on the hourly CISD being present
vs absent"). claim '+': confirmed extremes trade better.

All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C

RR = 2.0
MAX_HOLD = "23h"            # one full session of M1 bars (hold_basis="bars")


def detect(m1):
    d = C.daily(m1).reset_index()
    h = C.complete_bars(m1, "1h")
    cz = C.cisd_table(h)
    # week label: Monday date of the session (trading_day + 1 day, day opens 18:00 Sunday)
    sd = d["td"] + pd.Timedelta(days=1)
    d["wk"] = sd - pd.to_timedelta(sd.dt.dayofweek, unit="D")
    d["wk_low"] = d.groupby("wk")["low"].cummin()
    d["wk_high"] = d.groupby("wk")["high"].cummax()
    pl, ph = d["low"].shift(1), d["high"].shift(1)
    bull = (d["low"] < pl) & (d["close"] > pl) & (d["low"] <= d["wk_low"])
    bear = (d["high"] > ph) & (d["close"] < ph) & (d["high"] >= d["wk_high"])
    # hourly CISD inside the daily candle, extreme == the daily wick extreme
    ctd = cl.trading_day(cz["t"]) if len(cz) else pd.DatetimeIndex([])
    xtd = cl.trading_day(cz["extreme_start"]) if len(cz) else pd.DatetimeIndex([])
    cz = cz.assign(ctd=ctd, xtd=xtd)
    cz = cz[cz["ctd"] == cz["xtd"]]
    key_b = set(zip(cz.loc[cz["dir"] == 1, "ctd"], cz.loc[cz["dir"] == 1, "extreme_price"]))
    key_s = set(zip(cz.loc[cz["dir"] == -1, "ctd"], cz.loc[cz["dir"] == -1, "extreme_price"]))
    # confirmation must close inside the daily candle (ctd == day) -> known at the daily close
    h1_b = np.array([(t, lo) in key_b for t, lo in zip(d["td"], d["low"])], bool)
    h1_s = np.array([(t, hi) in key_s for t, hi in zip(d["td"], d["high"])], bool)
    rows = []
    for i in np.flatnonzero((bull | bear).to_numpy()):
        b, s = bool(bull.iloc[i]), bool(bear.iloc[i])
        if b and s:                       # two-sided C2: take the side carrying the H1 CISD
            if h1_b[i] == h1_s[i]:
                continue
            b, s = h1_b[i], h1_s[i]
        dirn = 1 if b else -1
        rows.append({"decision_time": d["close_time"].iloc[i],
                     "available_at": d["close_time"].iloc[i],
                     "direction": dirn,
                     "stop_px": float(d["low"].iloc[i] if b else d["high"].iloc[i]),
                     "rr": RR,
                     "h1_cisd": bool(h1_b[i] if b else h1_s[i]),
                     "weekday": int((d["td"].iloc[i] + pd.Timedelta(days=1)).dayofweek)})
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "h1_cisd", "weekday"]
    out = pd.DataFrame(rows, columns=cols)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = pd.DatetimeIndex(out["available_at"])
    return out


OP_PARAMS = {"daily_open": "18:00 NY", "c2_test": "low<prior low & close>prior low (mirror)",
             "week_extreme": "C2 extreme = week-to-date extreme (Mon-based week)",
             "h1_cisd": "phase-3 CISD (series_open, 2/2 swing, max_wait 3) on 1h, confirm and "
                        "extreme inside the daily candle, extreme == daily wick extreme",
             "rr": RR, "max_hold": MAX_HOLD, "hold_basis": "bars",
             "min_day_m1": C.MIN_DAY_M1, "entry": "next session open after the C2 close"}
SRC = {"daily_open": "method_spec: §1.4 daily open 18:00 canon",
       "c2_test": "method_spec: §3.2 C2 test",
       "week_extreme": "corpus: Qt7Ek4keMzs 'finding the high or the low' of the week; method_spec §2.5 weekly profiles",
       "h1_cisd": "phase3: locked CISD config; method_spec §2.4 hourly CISD inside the daily candle",
       "rr": "method_spec: §5.3 2R floor / fixed target",
       "max_hold": "declared-before-run: trade candle 3 = the next session only",
       "hold_basis": "declared-before-run: one session of trading minutes (weekend-safe)",
       "min_day_m1": "declared-before-run: README trap 6 stub-session floor",
       "entry": "method_spec: §2.5 trade the days after the confirmed extreme (candle 3)"}

if __name__ == "__main__":
    ev = cl.cache_frame("wpf_events_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["h1_cisd"].mean(), ev["weekday"].value_counts().sort_index().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    book = ev[ev["h1_cisd"]].reset_index(drop=True)

    # reading a -- the confirmed-extreme continuation trade
    def detect_a(m1):
        e = detect(m1)
        return e[e["h1_cisd"]].reset_index(drop=True)
    probe_a = cl.probe_lookahead(detect_a, book, lookback="30D")
    ra = cl.trade_test(book, max_hold=MAX_HOLD, hold_basis="bars")
    print({k: ra.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties")})
    cl.write_result("weekly-profile-framework", "a", ra,
                    operationalization={"rules": [
                        "daily candles on the 18:00 NY roll; stub sessions (<600 M1) dropped",
                        "bullish C2: low < prior day low and close > prior day low, and the low is "
                        "the lowest low of the week so far (bearish mirror on highs)",
                        "confirm: a 1h CISD in the C2 direction confirmed inside that daily candle "
                        "whose extreme equals the daily wick extreme",
                        "two-sided C2: keep only the side carrying the H1 CISD",
                        "decide at the daily close; enter at the next session open (candle 3); "
                        "stop at the confirmed extreme; target 2R; exit after one session"],
                        "params": OP_PARAMS},
                    params_source=SRC, script=__file__, probe=probe_a,
                    notes="Pre-existing HTF bias (sourced outside the unit) and the C4 add-on "
                          "are not modelled; the profile names only classify the weekday.")

    rb = cl.gate_test(ev, "h1_cisd", mask_available_at="decision_time",
                      max_hold=MAX_HOLD, hold_basis="bars")
    print({k: rb.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "gate_rate")})
    cl.write_result("weekly-profile-framework", "b", rb,
                    operationalization={"rules": [
                        "baseline: every daily C2 at the week-to-date extreme, traded as in "
                        "reading a (next-session entry, stop at the extreme, 2R, one session)",
                        "gate: the hourly CISD confirmation inside that daily candle is present "
                        "(known at the daily close)"], "params": OP_PARAMS},
                    params_source=SRC, script=__file__, probe=probe,
                    notes="Tests the framework's confirmation step (measurable: candle-3 "
                          "continuation with vs without the hourly CISD).")
