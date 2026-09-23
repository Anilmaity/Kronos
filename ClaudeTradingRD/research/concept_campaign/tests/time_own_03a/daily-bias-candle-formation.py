"""daily-bias-candle-formation — Daily bias from candle formation, including inside days
(TTrades own voice, specified: one reading).

Claim ('+'): the formation of the completed daily candle gives the next day's direction.
Operationalisation (detection_rules, in order):
  * C2 formation: the day swept the previous day's low and closed back above it ->
    bullish (mirror bearish). Two-sided days (both swept) carry no read.
  * Inside day ("where he does not expect the range to be exceeded but still reads the
    candle's internal formation"): open -> low first -> close up (the low printed before
    the high AND close > open) -> bullish; open -> high first -> close down -> bearish.
    Degenerate orders carry no read (invalidation: 'the formation is no longer clean').
  * Cross-check: a contrary 1h CISD inside the daily candle argues against the read ->
    no bias that day (detectors.bias.hourly_cisd_in_candle, scope 'range',
    series_open; the LTF is unnamed in the corpus, 1h is the spec §2.4 gate TF).
  * Weak close: "reduces expectation of a range break without flipping the read" ->
    ignored (no direction change).
Trade: decide at the biased day's close; enter the next session's first M1 open in the
bias direction; target = the biased day's bias-side extreme (the next day's 'previous
day high or low', execution.targets); stop = its opposite extreme; exit after one
session of trading time (1380 M1 bars). claim '+', trade_test vs matched control.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, OHLC, daily, show, MIN_DAY_M1   # noqa: E402
from detectors.bias import hourly_cisd_in_candle                 # noqa: E402

CID = "daily-bias-candle-formation"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "kind"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily(m1)
    if len(d) < 3:
        return pd.DataFrame(columns=COLS)
    td = cl.trading_day(m1.index)
    g_lo = m1["low"].groupby(td.values).idxmin()
    g_hi = m1["high"].groupby(td.values).idxmax()
    tdk = pd.DatetimeIndex(d["trading_day"])
    t_low = pd.DatetimeIndex(g_lo.reindex(tdk.values).to_numpy())
    t_high = pd.DatetimeIndex(g_hi.reindex(tdk.values).to_numpy())
    low_first = np.asarray(t_low < t_high)
    high_first = np.asarray(t_high < t_low)
    ok = d["p_ok"].to_numpy(bool)
    b_c2 = ((d["low"] < d["p_low"]) & (d["close"] > d["p_low"])).to_numpy()
    s_c2 = ((d["high"] > d["p_high"]) & (d["close"] < d["p_high"])).to_numpy()
    inside = ((d["high"] < d["p_high"]) & (d["low"] > d["p_low"])).to_numpy()
    b_in = inside & low_first & (d["close"] > d["open"]).to_numpy()
    s_in = inside & high_first & (d["close"] < d["open"]).to_numpy()
    bull = ok & ((b_c2 & ~s_c2) | b_in)
    bear = ok & ((s_c2 & ~b_c2) | s_in)
    kind = np.where(b_c2 | s_c2, "c2", "inside")
    h = cl.build_bars(m1, "1h")[OHLC]
    rows = []
    for i in np.flatnonzero(bull | bear):
        r = d.iloc[i]
        s = 1 if bull[i] else -1
        contrary = "bearish" if s > 0 else "bullish"
        end = pd.Timestamp(r["close_time"]) - pd.Timedelta(hours=1)
        if hourly_cisd_in_candle(h, d.index[i], end, contrary, scope="range",
                                 level_rule="series_open") is not None:
            continue
        stop = float(r["low"] if s > 0 else r["high"])
        tgt = float(r["high"] if s > 0 else r["low"])
        if s * (tgt - float(r["close"])) <= 0:
            continue
        ct = pd.Timestamp(r["close_time"])
        rows.append({"decision_time": ct, "available_at": ct, "direction": s,
                     "stop_px": stop, "target_px": tgt, "kind": kind[i]})
    return pd.DataFrame(rows, columns=COLS)


OP = {"rules": [
    "daily candles on the 18:00 NY roll; stub days (<600 M1) dropped; previous day must be "
    "the preceding real session (1-4 calendar days back)",
    "bullish: swept previous day low and closed back above it (one-sided); or an inside day "
    "whose low printed before its high (M1 timestamps) and closed above its open; bearish "
    "mirrored",
    "drop the read when a contrary 1h CISD (series_open, scope range) exists inside the day",
    "decide at the day's close; enter next M1 open in the bias direction; target = the "
    "day's bias-side extreme, stop = its opposite extreme; no-room rows dropped; exit after "
    "1380 trading M1 bars (hold_basis='bars'); control holds the NY clock (+/-30 min)"],
    "params": {"stub_filter_min_m1": MIN_DAY_M1, "cross_check_tf": "1h",
               "cisd_scope": "range", "cisd_level_rule": "series_open",
               "target": "biased day's bias-side extreme", "max_hold": "1380min",
               "hold_basis": "bars", "ctrl_tod_tol_min": 30}}
SRC = {"stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions (n_m1>=600)",
       "cross_check_tf": "method_spec: §2.4 hourly CISD is the confirmation TF; the concept's "
                         "ambiguity 'LTF never named' resolved to it before the run",
       "cisd_scope": "method_spec: §2.4 [P] scope default 'range'",
       "cisd_level_rule": "method_spec: §4.2 'carry first-candle-open as the sensible default'",
       "target": "corpus: execution.targets 'previous day high or low'",
       "max_hold": "declared-before-run: the bias is for the next session only",
       "hold_basis": "declared-before-run: README trap 7 — holds cross the 17:00 halt/weekend",
       "ctrl_tod_tol_min": "declared-before-run: every entry sits at the 18:00 reopen; hold "
                           "the NY clock fixed (README trap 9)"}

if __name__ == "__main__":
    ev = cl.cache_frame("dbcf_v1", lambda: detect(cl.load_m1()))
    ev = ev[pd.DatetimeIndex(ev["decision_time"]) <= cl.load_m1().index[-1]].reset_index(drop=True)  # the data\'s last, unfinished day
    print(len(ev), ev["direction"].value_counts().to_dict(), ev["kind"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold="1380min", hold_basis="bars", ctrl_tod_tol_min=30)
    show(res)
    p = cl.write_result(CID, None, res, operationalization=OP, params_source=SRC,
                        script=__file__, probe=probe,
                        notes="The discretionary 'slow and shallow' override (00iZXPAdR5A) has no "
                              "threshold and is not applied.")
    print(p)
