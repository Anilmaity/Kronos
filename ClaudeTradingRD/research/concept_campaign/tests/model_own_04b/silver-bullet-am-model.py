"""silver-bullet-am-model — trade_test.

Rule as taught (o0v4KQxZbpU): at 10:00 NY mark the 09:00 hourly candle's high/low;
inside 10:00-11:00 wait for a raid of ONE side; after the raid take a 1-minute entry
model in the opposite direction; stop on the swept extreme; target the OTHER side of
the 09:00 candle; no raid / no entry by 11:00 = no trade.

Operationalisation: the "entry model (breaker / OB / FVG)" is implemented as the
adjudicated 1-minute CISD (spec §4.2: close through the open of the first candle of
the opposing series that made the sweep extreme). First confirmed setup of the day
only. The 3R break-even rule is not applied (the harness resolves fixed stop/target;
the rule is also flagged as possibly a backtest-only convention).
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
MIN_BARS = 45          # holiday / stub guard for the 09:00 hour and the 10-11 window
MAX_HOLD = "120min"


def _utc_at(dates, hhmm):
    loc = pd.DatetimeIndex(dates) + pd.Timedelta(hhmm)
    return loc.tz_localize(NY, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    idx = pd.DatetimeIndex(m1.index)
    o, h, l, c = (m1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    dates = pd.DatetimeIndex(np.unique(idx.tz_convert(NY).tz_localize(None).normalize()))
    t9, t10, t11 = (_utc_at(dates, x) for x in ("9h", "10h", "10h59min"))
    a = idx.searchsorted(t9)
    b = idx.searchsorted(t10)
    e = idx.searchsorted(t11)
    rows = []
    for k in range(len(dates)):
        if b[k] - a[k] < MIN_BARS:
            continue
        H = h[a[k]:b[k]].max()
        L = l[a[k]:b[k]].min()
        best = None
        for bull, lvl in ((True, L), (False, H)):
            j, ext = cisd_after_sweep(o, h, l, c, b[k], e[k], lvl, bull, lo=a[k])
            if j >= 0 and (best is None or j < best[0]):
                best = (j, ext, bull)
        if best is None:
            continue
        j, ext, bull = best
        tgt = H if bull else L
        if (bull and c[j] >= tgt) or ((not bull) and c[j] <= tgt):
            continue
        dt = idx[j] + pd.Timedelta(minutes=1)
        rows.append({"decision_time": dt, "available_at": dt,
                     "direction": 1 if bull else -1, "stop_px": ext, "target_px": tgt})
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    return pd.DataFrame(rows, columns=cols)


if __name__ == "__main__":
    ev = cl.cache_frame("sb_am_1m_cisd_v2", lambda: detect(cl.load_m1()))
    print(len(ev), ev.head())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, ctrl_tod_tol_min=30)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "per NY calendar day: 09:00-10:00 NY hour high H / low L from M1 (>=45 bars)",
        "scan M1 bars 10:00-10:58 NY: a bar trading below L (or above H) arms the setup",
        "entry model = 1m CISD: close through the open of the first candle of the "
        "opposing-close series (<=10 candles) that made the running sweep extreme; a new "
        "extreme re-derives the series",
        "first confirmed side of the day only; decide at the confirming 1m close, enter "
        "next M1 open",
        "stop = sweep extreme; target = opposite side of the 09:00 candle; time exit 120 min",
        "control matched to NY time of day +/-30 min"],
        "params": {"hour_candle": "09:00 NY", "window": "10:00-11:00 NY",
                   "entry_model": "1m CISD series_open", "max_series": 10,
                   "min_bars": MIN_BARS, "max_hold": MAX_HOLD, "ctrl_tod_tol_min": 30,
                   "break_even_at_3R": "not applied"}}
    src = {"hour_candle": "corpus: o0v4KQxZbpU 'the previous hours high and low or the 9:00 a.m. hourly candle'",
           "window": "corpus: o0v4KQxZbpU 'these entries have to fall within 10 to 11: a.m. window'",
           "entry_model": "method_spec: §4.2 CISD adjudicated definition, first-candle-open default",
           "max_series": "method_spec: §4.2 / detectors.cisd default max_series=10",
           "min_bars": "declared-before-run: holiday/stub-session guard",
           "max_hold": "declared-before-run: 2h after entry, to the end of the NY AM session (08:30-12:00)",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9 — setup test, not a window test; hold NY clock fixed",
           "break_even_at_3R": "declared-before-run: harness resolves fixed stop/target; corpus flags it as backtest convention"}
    p = cl.write_result("silver-bullet-am-model", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="1m CISD stands in for the discretionary breaker/OB/FVG entry; "
                              "shallow-sweep and 'price coming back' discretionary skips not modelled.")
    print("wrote", p)
