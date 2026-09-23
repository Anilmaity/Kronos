"""dynamic-daily-bias (guest: Alex's Options, V8P6lNIisvc).

Measurable named by the concept: "expectancy of trades taken on the pre-open
bias vs trades taken on the intraday-updated bias". Gate test on the days and
moments where the two DISAGREE, so every trade sides with exactly one of them:

  baseline book  5m CISD events (phase-3 locked config), stop = protected swing,
                 2R, max hold 10 bars - restricted to moments where
    pre-open bias  = the channel's previous-candle engine on the prior trading
                     day's daily candle (continuation / reversal closure; inside ->
                     trend), i.e. the bias "set in stone in the morning", and
    dynamic bias   = direction of the latest intraday 15m structure shift of the
                     current trading day: a 15m candle CLOSING beyond the most recent
                     confirmed 2/2 swing high/low, with a same-direction FVG on the
                     leg (within the 4 bars ending at the break)
                 both exist and are opposite.
  gate           the CISD trades WITH the dynamic bias (complement: with the
                 pre-open bias). claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import swing_points, fair_value_gaps
from detectors.bias import previous_candle_state

RR = 2.0
MAX_HOLD = "50min"
MIN_DAY_M1 = 600
FVG_WIN = 4


def detect(m1):
    # ---- pre-open bias from the previous trading day's candle
    D = cl.build_bars(m1, "1D")
    D = D[D["n_m1"] >= MIN_DAY_M1]
    st = previous_candle_state(D[["open", "high", "low", "close"]])
    pre = st["implied_bias"].map({"bullish": 1, "bearish": -1}).fillna(0).to_numpy()
    d_close = cl.data.utc_ns(D["close_time"])
    # ---- intraday structure shifts on 15m
    Q = cl.build_bars(m1, "15min")
    Q = Q[Q["n_m1"] > 0]
    n = len(Q)
    sw = swing_points(Q, 2, 2)
    h, l, c = Q["high"].to_numpy(), Q["low"].to_numpy(), Q["close"].to_numpy()
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    pos = np.arange(n)
    mh = sw["swing_high"].to_numpy() & (pos + 2 < n)
    ml = sw["swing_low"].to_numpy() & (pos + 2 < n)
    sh[pos[mh] + 2] = h[mh]
    sl[pos[ml] + 2] = l[ml]
    sh = pd.Series(sh).ffill().shift(1).to_numpy()      # latest swing confirmed before bar j
    sl = pd.Series(sl).ffill().shift(1).to_numpy()
    cp = np.r_[np.nan, c[:-1]]
    g = fair_value_gaps(Q)
    bf = g["bullish_fvg"].rolling(FVG_WIN, min_periods=1).max().to_numpy() > 0
    rf = g["bearish_fvg"].rolling(FVG_WIN, min_periods=1).max().to_numpy() > 0
    up = (c > sh) & (cp <= sh) & bf
    dn = (c < sl) & (cp >= sl) & rf
    sdir = np.where(up & ~dn, 1, np.where(dn & ~up, -1, 0))
    q_close = pd.DatetimeIndex(Q["close_time"])
    q_day = np.asarray(cl.trading_day(Q.index), dtype="datetime64[ns]")
    keep = sdir != 0
    s_t, s_dir, s_day = cl.data.utc_ns(q_close[keep]), sdir[keep], q_day[keep]
    # ---- baseline: 5m CISD
    F = cl.build_bars(m1, "5min")
    F = F[F["n_m1"] > 0]
    cz = cisd_events(F[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    t = pd.DatetimeIndex(F.loc[cz["confirm_time"], "close_time"])
    t_ns = cl.data.utc_ns(t)
    e_day = np.asarray(cl.trading_day(pd.DatetimeIndex(cz["confirm_time"])), dtype="datetime64[ns]")
    direction = np.where(cz["direction"] == "bullish", 1, -1)
    kd = np.searchsorted(d_close, t_ns, side="right") - 1
    pre_b = np.where(kd >= 0, pre[np.maximum(kd, 0)], 0)
    # the prior daily candle must be the immediately previous trading day's: its
    # close must be within 4 days (skips data holes)
    gap_ok = (kd >= 0) & ((t_ns - d_close[np.maximum(kd, 0)]) < np.timedelta64(4, "D"))
    pre_b = np.where(gap_ok, pre_b, 0)
    ks = np.searchsorted(s_t, t_ns, side="right") - 1
    ks0 = np.maximum(ks, 0)
    dyn = np.where((ks >= 0) & (s_day[ks0] == e_day), s_dir[ks0], 0)
    sel = (pre_b != 0) & (dyn != 0) & (pre_b != dyn)
    ev = pd.DataFrame({
        "decision_time": t[sel], "available_at": t[sel],
        "direction": direction[sel],
        "stop_px": cz["protected_swing"].to_numpy()[sel],
        "rr": RR, "pre_bias": pre_b[sel], "dyn_bias": dyn[sel]})
    ev["with_dynamic"] = ev["direction"] == ev["dyn_bias"]
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("dynbias_5mcisd_15mshift", lambda: detect(cl.load_m1()))
    print(len(ev), ev.with_dynamic.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "with_dynamic", mask_available_at="decision_time",
                       max_hold=MAX_HOLD)
    for k in ("n", "n_complement", "gate_firing_rate", "avg_R", "diff", "ci_lo", "ci_hi",
              "p", "mde", "verdict", "verdict_detail", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "baseline: 5m CISD (series_open, 2/2, max_wait 3); stop protected swing; 2R; hold 50min",
        "pre-open bias: previous_candle_state on 1D candles (18:00 NY roll, days with >=600 M1) "
        "read from the last CLOSED daily candle (within 4 days)",
        "dynamic bias: latest 15m close beyond the most recent confirmed 2/2 swing high/low "
        "(first close through) with a same-direction 3-bar FVG within the 4 bars ending at "
        "the break, earlier in the SAME trading day, by the CISD's decision",
        "book restricted to events where both biases exist and disagree",
        "gate: CISD direction == dynamic bias; complement trades with the pre-open bias"],
        "params": {"entry_tf": "5min", "shift_tf": "15min", "fvg_window": FVG_WIN, "rr": RR,
                   "max_hold": MAX_HOLD, "min_day_m1": MIN_DAY_M1, "cisd": "phase3 locked"}}
    src = {"entry_tf": "corpus: V8P6lNIisvc (concept ltf 5m/1m); phase3 5m entry stack",
           "shift_tf": "corpus: V8P6lNIisvc (concept htf list 1D, 15m)",
           "fvg_window": "threshold_fits: displacement N=4 window; FVG on the leg per the concept",
           "rr": "method_spec §5.3: 2R floor",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "min_day_m1": "declared-before-run: skip stub sessions (README trap 6)",
           "cisd": "phase3: locked CISD config"}
    print(cl.write_result("dynamic-daily-bias", None, res, operationalization=op,
                          params_source=src, script=__file__, probe=probe,
                          notes="Compares trading with the intraday-updated bias vs the "
                                "pre-open (previous-candle) bias on the moments they disagree."))
