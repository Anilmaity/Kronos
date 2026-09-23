"""ny-morning-routine — trade_test.

The routine (Zm2oKad3Tb8) ends in an executable plan: daily draw -> mark the obvious
highs/lows and the midnight open -> after 08:30 look for the move BELOW the midnight
open that sweeps the marked low (classic buy day; mirrored for sell days) -> enter on
the lower timeframe with the stop at the swept low -> first target the marked high,
hold to the close.

Operationalisation (declared before the run):
  * daily draw/bias = the spec's mechanical previous-candle engine (§2.3) on the last
    CLOSED 18:00-NY daily candle: took the high & closed above -> bullish, took the
    high & closed back inside -> bearish (mirrored); inside bar -> last resolved trend;
    both sides taken -> no trade.
  * "obvious" 15m highs/lows = the external range of 00:00-08:30 NY (midnight open to
    the 08:30 release) — the move below it is necessarily a move below the midnight open.
  * entry = 5m CISD after the sweep (spec §2.4 session map: New York confirms on 5m/15m),
    inside 08:30-12:00 NY; stop = the swept extreme; target = the opposite side of the
    00:00-08:30 range (the marked high); time exit at 16:00 NY ("hold to close").
  * the calendar step is not modelled (no event calendar in the data); 08:30 is used as
    the time marker every day, as in his worked example.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _helpers import cisd_after_sweep  # noqa: E402

NY = "America/New_York"
MIN_PRE_BARS = 300     # the 00:00-08:30 window must be substantially traded (510 max)


def _utc_at(dates, hhmm):
    loc = pd.DatetimeIndex(dates) + pd.Timedelta(hhmm)
    return loc.tz_localize(NY, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")


def daily_bias(d: pd.DataFrame) -> pd.Series:
    """Implied bias for the NEXT day, from each closed daily candle (spec §2.3)."""
    h, l, c = d["high"], d["low"], d["close"]
    ph, pl = h.shift(1), l.shift(1)
    th, tl = (h > ph).fillna(False), (l < pl).fillna(False)
    b = pd.Series(np.nan, index=d.index)
    b[th & ~tl & (c > ph)] = 1
    b[th & ~tl & ~(c > ph)] = -1
    b[tl & ~th & (c < pl)] = -1
    b[tl & ~th & ~(c < pl)] = 1
    trend = pd.Series(np.where(th & ~tl, 1, np.where(tl & ~th, -1, np.nan)), index=d.index).ffill()
    inside = ~th & ~tl
    b[inside] = trend[inside]
    b[th & tl] = 0
    return b.fillna(0)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    d = d.assign(bias=daily_bias(d))
    b5 = cl.build_bars(m1, "5min")
    idx5 = pd.DatetimeIndex(b5.index)
    o, h, l, c = (b5[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct5 = pd.DatetimeIndex(b5["close_time"])
    midx = pd.DatetimeIndex(m1.index)
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    dates = pd.DatetimeIndex(np.unique(midx.tz_convert(NY).tz_localize(None).normalize()))
    t0, t830, t12, t16 = (_utc_at(dates, x) for x in ("0h", "8h30min", "12h", "16h"))
    a1 = midx.searchsorted(t0)
    b1 = midx.searchsorted(t830)
    s5 = idx5.searchsorted(t830)
    e5 = idx5.searchsorted(t12 - pd.Timedelta(minutes=5))   # 5m bars closing by 12:00
    lo5 = idx5.searchsorted(t830 - pd.Timedelta(hours=2))
    prior = cl.asof(d, t830)                                  # last CLOSED daily candle
    rows = []
    for k in range(len(dates)):
        if b1[k] - a1[k] < MIN_PRE_BARS:
            continue
        bias = prior["bias"].iloc[k]
        if not np.isfinite(bias) or bias == 0:
            continue
        H = mh[a1[k]:b1[k]].max()
        L = ml[a1[k]:b1[k]].min()
        bull = bias > 0
        j, ext = cisd_after_sweep(o, h, l, c, s5[k], e5[k], L if bull else H, bull,
                                  lo=lo5[k])
        if j < 0:
            continue
        tgt = H if bull else L
        if (bull and c[j] >= tgt) or ((not bull) and c[j] <= tgt):
            continue
        dt = ct5[j]
        rows.append({"decision_time": dt, "available_at": dt,
                     "direction": 1 if bull else -1, "stop_px": ext, "target_px": tgt,
                     "max_hold": t16[k] - dt})
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    return pd.DataFrame(rows, columns=cols)


if __name__ == "__main__":
    ev = cl.cache_frame("ny_routine_5m_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev.head())
    probe = cl.probe_lookahead(detect, ev, lookback="8D")
    res = cl.trade_test(ev, ctrl_tod_tol_min=30)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "bias: previous-candle engine on the last closed 18:00-NY daily candle "
        "(continuation/reversal closure; inside -> last trend; both sides -> skip)",
        "marked levels: high/low of 00:00-08:30 NY (>=300 M1 bars)",
        "bullish day: after 08:30 a 5m bar trades below the 00:00-08:30 low (necessarily "
        "below the midnight open); entry = 5m CISD (close through the first open of the "
        "down-close series that made the running low); mirrored for bearish days",
        "confirming 5m bar must close by 12:00 NY; decide at its close, enter next M1 open",
        "stop = swept extreme; target = opposite side of the 00:00-08:30 range; time exit 16:00 NY",
        "control matched to NY time of day +/-30 min"],
        "params": {"bias_rule": "previous-candle engine §2.3", "marked_range": "00:00-08:30 NY",
                   "entry_tf": "5min CISD series_open", "entry_window": "08:30-12:00 NY",
                   "exit_time": "16:00 NY", "min_pre_bars": MIN_PRE_BARS,
                   "ctrl_tod_tol_min": 30, "day_open_hour": 18}}
    src = {"bias_rule": "method_spec: §2.3 previous-candle engine (the mechanical draw)",
           "marked_range": "corpus: Zm2oKad3Tb8 'you can also mark out the midnight opening price' + 'we want to see a move below that in order to get long'",
           "entry_tf": "method_spec: §2.4 session map (New York confirms on 5m or 15m) + §4.2 CISD",
           "entry_window": "session_window_fit: ny_am 08:30-12:00 widest attested window",
           "exit_time": "declared-before-run: 'hold to close' = end of the NY cash session 16:00",
           "min_pre_bars": "declared-before-run: stub/holiday guard",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9 — setup test, NY clock held fixed",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily candle"}
    p = cl.write_result("ny-morning-routine", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Economic-calendar step not modelled (no calendar data); "
                              "'obvious highs/lows' fixed as the midnight-08:30 external range.")
    print("wrote", p)
