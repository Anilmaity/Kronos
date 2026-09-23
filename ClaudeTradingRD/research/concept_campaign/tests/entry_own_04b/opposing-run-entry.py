"""opposing-run-entry — contested, two readings.

(a) trade_test — the time-level opposing run (EYzP7c24AwM, daily-profile videos): with a
    daily bias, at 00:00 / 08:30 / 09:30 NY price runs COUNTER to the bias from the time
    level's open, printing a series of opposing candles; the close back through that series
    validates it as an order block. Enter on that close, stop beyond the run's extreme,
    2R target (the concept's own measurable: "hit rate of 2R from those entries").
(b) gate_test — the earlier recording's price anchor (b6yvRKf8haE): the Judas swing that must
    be caught sits beyond BOTH the midnight open and the 08:30 open (below them on a buy
    day). Baseline = reading (a)'s 08:30/09:30 book (where both opens are known at the
    decision); gate = the run's extreme lies beyond both opens on the required side.

All parameters are declared here before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.bias import previous_candle_state

TF = "5min"
MAX_WAIT = 3
SWING = 2
LEVELS = ("00:00", "08:30", "09:30")
RUN_WIN_MIN = 30          # the run's extreme must start within 30 min of the time level
RR = 2.0
EXIT_NY = "16:00"         # hold until the end of the NY session


def _bias(m1: pd.DataFrame, t: pd.DatetimeIndex) -> np.ndarray:
    d = cl.build_bars(m1, "1D")
    st = previous_candle_state(d[["open", "high", "low", "close"]])
    d = d.assign(bias=st["implied_bias"].map({"bullish": 1, "bearish": -1}).fillna(0))
    a = cl.asof(d, t)                       # last COMPLETED day; its bias is for today
    bias = a["bias"].to_numpy(float).copy()
    # the asof day must be the immediately preceding trading day
    td_prev = pd.DatetimeIndex(a["trading_day"])
    today = cl.trading_day(t)
    ok = np.asarray((today - td_prev) <= pd.Timedelta(days=3))
    bias[~ok | np.isnan(bias)] = 0
    return bias


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold",
            "level_hhmm", "run_extreme", "beyond_both"]
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=SWING, right=SWING, max_wait=MAX_WAIT, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    dec = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    ext_t = pd.DatetimeIndex(ev["extreme_time"])
    mod = cl.ny_minute_of_day(ext_t)
    dirn = np.where(ev["direction"] == "bullish", 1, -1)
    ext = ev["protected_swing"].to_numpy(float)
    out = []
    for hhmm in LEVELS:
        a = int(hhmm[:2]) * 60 + int(hhmm[3:])
        sel = (mod >= a) & (mod < a + RUN_WIN_MIN)
        if not sel.any():
            continue
        t = dec[sel]
        op = cl.open_at(t, hhmm, m1=m1)["price"].to_numpy(float)
        # the open must belong to the same trading day as the run's extreme
        same = np.asarray(cl.trading_day(t) == cl.trading_day(ext_t[sel]))
        dd, xx = dirn[sel], ext[sel]
        counter = np.where(dd > 0, xx < op, xx > op)       # ran against the bias from the open
        df = pd.DataFrame({"decision_time": t, "direction": dd, "stop_px": xx,
                           "level_hhmm": hhmm, "run_extreme": xx, "ok": counter & same})
        out.append(df[df["ok"]].drop(columns="ok"))
    if not out:
        return pd.DataFrame(columns=cols)
    df = pd.concat(out).sort_values("decision_time").reset_index(drop=True)
    t = pd.DatetimeIndex(df["decision_time"])
    df = df[_bias(m1, t) == df["direction"].to_numpy()].reset_index(drop=True)
    if df.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(df["decision_time"])
    # one trade per (trading day, time level): the first confirmation
    df["_k"] = cl.trading_day(t).astype(str) + df["level_hhmm"]
    df = df.groupby("_k", sort=False).head(1).reset_index(drop=True)
    t = pd.DatetimeIndex(df["decision_time"])
    ny = t.tz_convert("America/New_York")
    end = (ny.normalize() + pd.Timedelta(hours=16)).tz_localize(None).tz_localize(
        "America/New_York", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")
    df["max_hold"] = end - t
    df = df[df["max_hold"] > pd.Timedelta(minutes=5)].reset_index(drop=True)
    t = pd.DatetimeIndex(df["decision_time"])
    mo = cl.open_at(t, "00:00", m1=m1)["price"].to_numpy(float)
    o830 = cl.open_at(t, "08:30", m1=m1)["price"].to_numpy(float)
    d = df["direction"].to_numpy()
    x = df["run_extreme"].to_numpy(float)
    both = np.where(d > 0, (x < mo) & (x < o830), (x > mo) & (x > o830))
    df["beyond_both"] = np.where(np.isnan(mo) | np.isnan(o830), False, both)
    df["available_at"] = df["decision_time"]
    df["rr"] = RR
    return df[cols].reset_index(drop=True)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    df = detect(m1)
    return df[df["level_hhmm"].isin(["08:30", "09:30"])].reset_index(drop=True)


SRC = {"tf": "corpus: concept ltf 15m/5m/1m; method_spec §1.2 1-hour/5-minute pairing",
       "max_wait": "phase3: locked CISD config (close-through within 3 bars)",
       "swing": "phase3: locked 2/2 swing",
       "levels": "corpus: EYzP7c24AwM 'at midnight, 08:30 and 09:30' (concept detection rule 1)",
       "run_win_min": "declared-before-run: 'at' a time level = run extreme within 30 min",
       "rr": "corpus: concept measurable 'hit rate of 2R from those entries'; method_spec §5.3",
       "exit_ny": "declared-before-run: hold to 16:00 NY (end of the NY session)",
       "hold_basis": "declared-before-run: holds end at 16:00 NY, up to 16h; controls must "
                     "not lose exposure to the 17:00 halt/weekend (trap 7)",
       "bias": "method_spec: §2.3 previous-candle engine (implied_bias of the prior day)"}
PARAMS = {"tf": TF, "max_wait": MAX_WAIT, "swing": SWING, "levels": LEVELS,
          "run_win_min": RUN_WIN_MIN, "rr": RR, "exit_ny": EXIT_NY, "hold_basis": "bars",
          "bias": "previous_candle_state implied_bias, 1D bars, 18:00 NY roll"}
RULES_A = [
    "daily bias = previous-candle engine on the prior completed trading day (continuation/"
    "reversal closure); no-bias days skipped",
    "5m CISD (series_open, 2/2 swings, close within 3 bars) in the bias direction whose "
    "opposing run's extreme bar starts within 30 min after 00:00, 08:30 or 09:30 NY and lies "
    "beyond that time level's open against the bias (the opposing run)",
    "enter next M1 open after the confirming close; stop = the run's extreme; target 2R; "
    "exit at 16:00 NY; first confirmation per (day, time level)"]


def show(res):
    for k in ("n", "n_other", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail"):
        print(" ", k, res.get(k))


if __name__ == "__main__":
    ev = cl.cache_frame(f"orun_{TF}_mw{MAX_WAIT}_w{RUN_WIN_MIN}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["level_hhmm"].value_counts().to_dict(), ev["beyond_both"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, hold_basis="bars", cluster=ev["decision_time"].dt.tz_convert(
        "America/New_York").dt.date.astype(str).to_numpy())
    print("reading a"); show(res)
    print("exposure", res.get("exposure_bars"))
    pa = cl.write_result("opposing-run-entry", "a", res,
                         operationalization={"rules": RULES_A, "params": PARAMS},
                         params_source=SRC, script=__file__, probe=probe,
                         notes="cluster = NY calendar date (several time levels per day)")
    print(pa)

    evb = cl.cache_frame(f"orun_b_{TF}_mw{MAX_WAIT}_w{RUN_WIN_MIN}",
                         lambda: detect_b(cl.load_m1()))
    probe_b = cl.probe_lookahead(detect_b, evb, lookback="20D")
    resb = cl.gate_test(evb, "beyond_both", mask_available_at="decision_time",
                        hold_basis="bars",
                        cluster=evb["decision_time"].dt.tz_convert(
                            "America/New_York").dt.date.astype(str).to_numpy())
    print("reading b"); show(resb)
    pb = cl.write_result("opposing-run-entry", "b", resb,
                         operationalization={"rules": RULES_A[:2] + [
                             "baseline: reading (a)'s 08:30 and 09:30 trades only (both opens "
                             "known at the decision)",
                             "gate beyond_both: the run's extreme is below both the midnight "
                             "open and the 08:30 open (buy day; above both on a sell day)",
                             RULES_A[2]], "params": PARAMS},
                         params_source={**SRC, "gate": "corpus: b6yvRKf8haE 'normally that is "
                                        "above the 8:30 and midnight open'"},
                         script=__file__, probe=probe_b,
                         notes="cluster = NY calendar date")
    print(pb)
