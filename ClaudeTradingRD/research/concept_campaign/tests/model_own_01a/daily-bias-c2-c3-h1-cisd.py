"""daily-bias-c2-c3-h1-cisd — Daily Bias = Daily C2/C3 Closure Confirmed by H1 CISD (contested).

Claim ('+'): the channel's "mechanical framework" for daily bias gives a direction worth
trading. Two distinct readings exist in the concept itself:

  a  REVERSAL BRANCH, same day (definition: "price opens, trades into the previous day
     high/low, a lower-timeframe change in the state of delivery confirms the wick, and
     price trades back into the range toward the EQ or the opposite previous-day
     extreme"). Operationalised on 1h: a CISD (detectors.cisd, series_open, 2/2 swing,
     max_wait 3 — phase3 locked) whose extreme swept the previous day's low (bullish) /
     high (bearish) and is the day's running extreme at the confirm close. Enter at the
     confirming 1h close; stop = the wick extreme (execution.stop 'On the confirmed wick
     extreme'); target = the opposite previous-day extreme (execution.targets first
     item); time exit at the day's 17:00 NY close. One CISD per day (spec §2.4
     'only one CISD per day') -> first qualifying event per trading day.

  b  NEXT-DAY BIAS (detection: "Find a candle 2 or candle 3 closure on the daily. Require a
     change in the state of delivery on the hourly in the same direction ... With both
     present, the day's bias is set"). Daily C2 (detectors.fractal) or C3 closure
     (Reading A reference, C2 opening price) on day D plus an hourly CISD inside D in the
     same direction (detectors.bias.hourly_cisd_in_candle, scope 'range', series_open).
     Trade D+1 from D's close toward D's bias-side extreme (the previous day high/low
     from D+1's view — execution.targets), stop at D's wick extreme (execution.stop),
     time exit after one session of trading bars.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import (cl, np, pd, OHLC, daily, c2c3_h1_bias, next_candle_draw_events,  # noqa: E402
                     cisd_events, day_end_utc, MIN_DAY_M1)

READ = sys.argv[1] if len(sys.argv) > 1 else "a"


def detect_a(m1):
    d = daily(m1)
    h = cl.build_bars(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    ev = cisd_events(h[OHLC], level_rule="series_open", left=2, right=2, max_wait=3,
                     min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    ct = pd.DatetimeIndex(ev["confirm_time"])
    dec = pd.DatetimeIndex(h.loc[ct, "close_time"])
    td = cl.trading_day(ct)
    ext_td = cl.trading_day(pd.DatetimeIndex(ev["extreme_time"]))
    prev = cl.asof(d, ct)                               # last completed day by the bar start
    gap = (td - pd.DatetimeIndex(prev["trading_day"])).days
    # running extreme of the trading day through the confirm bar (closed 1h bars only)
    hh = h[OHLC].copy()
    hh["tday"] = cl.trading_day(h.index)
    g = hh.groupby("tday", sort=False)
    run_lo = g["low"].cummin().loc[ct].to_numpy()
    run_hi = g["high"].cummax().loc[ct].to_numpy()
    bull = (ev["direction"] == "bullish").to_numpy()
    xp = ev["extreme_price"].to_numpy(float)
    pdl, pdh = prev["low"].to_numpy(float), prev["high"].to_numpy(float)
    swept = np.where(bull, xp < pdl, xp > pdh)
    is_day_ext = np.where(bull, np.isclose(xp, run_lo), np.isclose(xp, run_hi))
    ok = (np.asarray(td == ext_td) & np.asarray((gap >= 1) & (gap <= 4)) & swept & is_day_ext)
    out = pd.DataFrame({
        "decision_time": dec, "available_at": dec,
        "direction": np.where(bull, 1, -1),
        "stop_px": xp,
        "target_px": np.where(bull, pdh, pdl),
        "max_hold": day_end_utc(td) - dec,
        "tday": td,
    })[ok]
    out = out[out["max_hold"] > pd.Timedelta(0)]
    out = out.sort_values("decision_time").drop_duplicates("tday", keep="first")
    return out[cols].reset_index(drop=True)


def detect_b(m1):
    return next_candle_draw_events(c2c3_h1_bias(m1, scope="range", c3_reference="c2_open"))


if READ == "a":
    detect, key, lb = detect_a, "dbc2_a_intraday_rev", "10D"
    kw = dict()
else:
    detect, key, lb = detect_b, "dbc2_b_nextday", "20D"
    kw = dict(max_hold="1380min", hold_basis="bars")

ev = cl.cache_frame(key, lambda: detect(cl.load_m1()))
print(READ, "events", len(ev), ev["direction"].value_counts().to_dict())
probe = cl.probe_lookahead(detect, ev, lookback=lb)
print("probe", probe.get("passed"))
res = cl.trade_test(ev, **kw)
for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
          "ties", "exposure_bars", "ctrl_overlap", "halves"):
    print(k, res.get(k))

if READ == "a":
    op = {"rules": [
        "1h bars (UTC-aligned); CISD = close through the OPEN of the first candle of the "
        "opposing-close run into a 2/2 fractal swing, within 3 bars (detectors.cisd)",
        "the CISD extreme must sweep the previous completed (non-stub) day's low (bullish) / "
        "high (bearish), lie in the same trading day as the confirm bar, and equal the day's "
        "running extreme at the confirm close (it is the day's wick so far)",
        "first qualifying CISD per trading day only",
        "decide at the confirming 1h bar's close; enter next M1 open",
        "stop = the CISD extreme (wick); target = previous day's opposite extreme; "
        "time exit at 17:00 NY of that trading day (wall clock, no halt inside)"],
        "params": {"ltf": "1h", "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                   "min_series": 1, "target": "opposite previous-day extreme",
                   "max_hold": "to 17:00 NY same day", "stub_filter_min_m1": MIN_DAY_M1,
                   "one_per_day": True}}
    src = {"ltf": "corpus: daily-bias-c2-c3-h1-cisd 'Require a change in the state of delivery on the hourly'",
           "level_rule": "phase3: locked CISD level rule (first-candle open), method_spec §4.2",
           "swing": "phase3: locked swing fractal left=2,right=2",
           "max_wait": "phase3: locked CISD speed max_wait=3 (v-shape-reversal-speed)",
           "min_series": "phase3: locked min_series=1",
           "target": "corpus: execution.targets 'previous day high / low' (first listed)",
           "max_hold": "declared-before-run: the reversal branch trades the reversal DAY itself",
           "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions (n_m1>=600)",
           "one_per_day": "method_spec: §2.4 'There is only one CISD per day'"}
else:
    op = {"rules": [
        "daily candles 18:00 NY roll, stub days (<600 M1) removed",
        "daily C2 closure (detectors.fractal.c2_events: sweep prior candle extreme, close back "
        "inside, close in reversal direction) or C3 closure (prior candle took the extreme "
        "with no C2; close beyond C2's OPENING price) — detectors.bias.daily_closures",
        "confirmation: a 1h CISD inside that day in the same direction "
        "(hourly_cisd_in_candle, scope=range, series_open); either leg missing -> no bias",
        "decide at the day's close_time; trade the next session in the bias direction",
        "target = the biased day's bias-side extreme (PDH/PDL from the traded day), "
        "stop = its opposite (wick) extreme; exit after 1380 trading M1 bars"],
        "params": {"c3_reference": "c2_open", "cisd_scope": "range", "cisd_level": "series_open",
                   "max_hold": "1380min", "hold_basis": "bars", "stub_filter_min_m1": MIN_DAY_M1}}
    src = {"c3_reference": "phase3: locked primary C3 reference (Reading A, C2 opening price)",
           "cisd_scope": "phase3: locked primary cisd_scope=range",
           "cisd_level": "phase3: locked CISD level rule (first-candle open)",
           "max_hold": "declared-before-run: the bias is for the next session only",
           "hold_basis": "declared-before-run: README trap 7 — exits cross the 17:00 halt and weekends",
           "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions (n_m1>=600)"}
p = cl.write_result("daily-bias-c2-c3-h1-cisd", READ, res, operationalization=op,
                    params_source=src, script=__file__, probe=probe,
                    notes="Small-wick tradeability gate on the reversal day is not applied in "
                          "reading a (the day's wick is only known at its close).")
print(p)
