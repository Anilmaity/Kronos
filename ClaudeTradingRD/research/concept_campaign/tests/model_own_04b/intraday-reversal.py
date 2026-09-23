"""intraday-reversal — rate_test.

Claim (m0wTBdUe7gs): "a 4hour candle closure plus an hourly change [in the state of]
delivery" fixes the low (high) of the day; that extreme is then treated as the day's
low and traded away from. Measurable (yaml): hit rate of the declared session extreme
actually holding for the session.

Operationalisation:
  * 4H candle (forex grid) is a C2 closure: took the previous 4H low and closed back
    above it (mirrored for highs) — "a 4-hour candle closure taking out a low";
  * inside that 4H candle, a 1H CISD in the reversal direction (the 4H candle's
    extreme, the down-close 1H series that made it, a later 1H close through the
    series' first open, before the 4H close);
  * the 4H extreme is also the trading day's extreme so far ("fixes the low of the day");
  * decided at the 4H close. Outcome: the extreme is NOT traded through before the
    end of the NY trading day (18:00 roll). 4H candles closing at 17:00 NY are skipped.
  * null: the same distance below (above) the first price after a matched random
    moment (+/-30 d, NY time of day +/-30 min), same number of M1 bars, not touched.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _helpers import c2_flags, cisd_in_candle, day_end_bars, matched_touch_null  # noqa: E402

def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b4 = cl.build_bars(m1, "4h", grid4h="forex")
    b1 = cl.build_bars(m1, "1h")
    o4, h4, l4, c4 = (b4[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    o1, h1, l1, c1 = (b1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct4 = pd.DatetimeIndex(b4["close_time"])
    st4 = pd.DatetimeIndex(b4.index)
    i1 = pd.DatetimeIndex(b1.index)
    td4 = cl.trading_day(pd.DatetimeIndex(b4["first_m1"])).to_numpy()
    c2 = c2_flags(o4, h4, l4, c4)
    a = i1.searchsorted(st4)
    b = i1.searchsorted(ct4)
    last_close = pd.DatetimeIndex(m1.index)[-1] + pd.Timedelta(minutes=1)
    ny_close_hour = ct4.tz_convert("America/New_York").hour
    rows = []
    for i in range(1, len(b4)):
        if c2[i] == 0 or ct4[i] > last_close or ny_close_hour[i] == 17:
            continue
        bull = c2[i] > 0
        j, e = cisd_in_candle(o1, h1, l1, c1, a[i], b[i], bull)
        if j < 0:
            continue
        same = np.flatnonzero(td4[:i + 1] == td4[i])
        if bull and l4[i] > l4[same].min():
            continue
        if (not bull) and h4[i] < h4[same].max():
            continue
        rows.append({"decision_time": ct4[i], "available_at": ct4[i],
                     "direction": 1 if bull else -1,
                     "level": l4[i] if bull else h4[i]})
    return pd.DataFrame(rows, columns=["decision_time", "available_at", "direction", "level"])


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame("ir_4h_c2_1h_cisd_v2", lambda: detect(cl.load_m1()))
    t = pd.DatetimeIndex(ev["decision_time"])
    hb = day_end_bars(m1.index, t)
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="6D")
    mkt = cl.get_market()
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    lvl = ev["level"].to_numpy()
    side = np.where(ev["direction"].to_numpy() > 0, "below", "above")
    obs = np.zeros(len(ev), bool)
    for sd in ("above", "below"):
        m = side == sd
        obs[m] = ~cl.touch(t[m], lvl[m], sd, horizon_bars=hb[m])["hit"].to_numpy()
    dist = lvl - px
    null_fn = matched_touch_null(t, dist, side, hb, tod_tol_min=30, invert=True)
    res = cl.rate_test(obs.astype(float), t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev)
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "4H forex-grid candle is a C2 closure (took prior 4H low, closed back above; mirrored)",
        "1H CISD inside it: 4H extreme, the opposing 1H series that made it, a later 1H close "
        "through the series' first open before the 4H close",
        "the 4H extreme is the trading day's extreme so far (18:00 NY roll)",
        "decide at the 4H close (candles closing at 17:00 NY, the day end, are skipped); "
        "outcome = extreme not traded through before the trading day ends (M1 bars)",
        "null: same signed distance from first price after a matched random moment (+/-30d, "
        "NY time of day +/-30 min), same M1-bar horizon, not touched"],
        "params": {"grid4h": "forex", "cisd_tf": "1h", "level_rule": "series_open",
                   "horizon": "rest of NY trading day (M1 bars)", "skip_close_hour_ny": 17,
                   "null_tod_tol_min": 30, "day_open_hour": 18}}
    src = {"grid4h": "session_window_fit: forex grid for gold (carried as knob; forex is the declared default)",
           "cisd_tf": "corpus: m0wTBdUe7gs 'a 4hour candle closure plus an hourly change delivery'",
           "level_rule": "method_spec: §4.2 first-candle-open default",
           "horizon": "corpus: intraday-reversal yaml 'That extreme is then treated as the low of the day'",
           "skip_close_hour_ny": "declared-before-run: a 4H candle closing at the 17:00 halt leaves no session to hold",
           "null_tod_tol_min": "declared-before-run: README trap 9 — hold NY clock fixed in the null",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily candle"}
    p = cl.write_result("intraday-reversal", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe)
    print("wrote", p)
