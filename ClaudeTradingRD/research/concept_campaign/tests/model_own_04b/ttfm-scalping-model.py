"""ttfm-scalping-model — trade_test.

Model (eywpZT3z6GQ): an HOURLY candle 2 or candle 3 closure -> anticipate an hourly
expansion candle; find the 15-minute swing that forms that hourly candle's wick with a
15-minute candle-2 closure; enter a continuation and "trade the body of the hourly
candle"; stop at the protected swing; target 2R.

Operationalisation (declared before the run):
  * bias: the last CLOSED 1H candle is a C2 closure (§3.2) or a Reading-A C3 closure
    (§3.3) -> direction for the next hourly candle;
  * inside that next hour, the first 15m bar that is a C2 closure in the bias direction
    AND whose extreme is the hour's extreme so far (it forms the hourly wick), closing
    by :45 (so the entry is inside the hourly body);
  * entry at that 15m close (the positional entry at the open of the 15m C3); stop at
    the 15m C2 extreme (protected swing); target 2R; time exit 60 min.
  * the 1-minute CISD refinement and the daily-context filter are not modelled (the
    daily/hourly interaction is unstated; the 15m C2 close-back-inside is itself the
    lower-timeframe change of delivery at that swing).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _helpers import c2_flags, c3_flags  # noqa: E402

RR = 2.0
MAX_HOLD = "60min"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b1 = cl.build_bars(m1, "1h")
    o, h, l, c = (b1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    c2 = c2_flags(o, h, l, c)
    c3 = c3_flags(o, h, l, c, c2)
    b1 = b1.assign(bias=np.where(c2 != 0, c2, c3).astype(float))
    q = cl.build_bars(m1, "15min")
    qo, qh, ql, qc = (q[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    qc2 = c2_flags(qo, qh, ql, qc)
    qs = pd.DatetimeIndex(q.index)
    hour = qs.floor("1h")
    pos_in_hour = ((qs - hour) / pd.Timedelta(minutes=15)).astype(int).to_numpy()
    bias = cl.asof(b1, hour)["bias"].to_numpy()          # last CLOSED hourly candle
    hk = hour.asi8
    newh = np.r_[True, hk[1:] != hk[:-1]]
    grp = np.cumsum(newh)
    run_lo = pd.Series(ql).groupby(grp).cummin().to_numpy()
    run_hi = pd.Series(qh).groupby(grp).cummax().to_numpy()
    bull = (bias == 1) & (qc2 == 1) & (ql <= run_lo)
    bear = (bias == -1) & (qc2 == -1) & (qh >= run_hi)
    ok = (bull | bear) & (pos_in_hour <= 2)
    ok &= np.r_[False, np.ones(len(q) - 1, bool)]       # needs a previous 15m bar
    first = pd.Series(ok).groupby(grp).cumsum().to_numpy() == 1
    sel = np.flatnonzero(ok & first)
    ct = pd.DatetimeIndex(q["close_time"])[sel]
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": np.where(bull[sel], 1, -1),
                         "stop_px": np.where(bull[sel], ql[sel], qh[sel]),
                         "rr": RR})


if __name__ == "__main__":
    ev = cl.cache_frame("ttfm_scalp_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="6D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "bias: last closed 1H candle is a C2 closure (took prior hour's extreme, closed back "
        "inside) or a Reading-A C3 closure -> next hour's direction",
        "in the next hour: first 15m C2 closure in the bias direction whose extreme is the "
        "hour's extreme so far, closing by :45",
        "decide at that 15m close, enter next M1 open; stop at the 15m C2 extreme; 2R; 60 min"],
        "params": {"bias_tf": "1h", "swing_tf": "15min", "c3_reading": "A (close beyond C2 open)",
                   "rr": RR, "max_hold": MAX_HOLD, "last_c2_slot": ":30-:45"}}
    src = {"bias_tf": "corpus: eywpZT3z6GQ 'trading the body of the hourly candle using a 15-minute and 1 minute'",
           "swing_tf": "corpus: eywpZT3z6GQ 'trading the body of the hourly candle using a 15-minute and 1 minute'",
           "c3_reading": "method_spec: §3.3 Reading A (this unit's dedicated shorts)",
           "rr": "corpus: ttfm-scalping-model yaml targets '2R' (measurable: hit rate of 2R)",
           "max_hold": "declared-before-run: one hourly candle — the trade lives inside the hourly body",
           "last_c2_slot": "declared-before-run: the 15m C2 must close before the hourly candle does"}
    p = cl.write_result("ttfm-scalping-model", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="1m CISD refinement and daily-context veto not modelled; entry is the "
                              "positional 15m-C3-open variant the execution field names.")
    print("wrote", p)
