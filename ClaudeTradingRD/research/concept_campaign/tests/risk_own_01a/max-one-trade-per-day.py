"""max-one-trade-per-day — gate: is the first signal of the trading day better than the rest?

The cap itself is a behavioural remedy (tilt, revenge trading), but the concept's own
measurables are "expectancy of the first signal of the day vs later signals" and
"P&L per day capped at one trade vs uncapped, same signal set". Under a hard cap only
the day's first qualifying signal is traded; every later signal is skipped. The only
market-decidable content of the cap is therefore: first-of-day signals >= later ones.

Baseline book: 15m CISD (the concept's execution timeframes are 15m/1m; 15m is the
phase-3 entry TF of the 4H/15m stack), stop at the protected swing, fixed 2R — the
concept's paired rule "exit at 2R or -1R, do not manage". Day = trading day rolling
at 18:00 NY. Gate first_of_day = no earlier 15m CISD decision in the same trading day
(knowable at the decision). claim '+'.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_raw, PHASE3_SRC  # noqa: E402

CID = "max-one-trade-per-day"
HOLD = "150min"


def detect(m1):
    b, ev = cisd_raw(m1, "15min")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "first_of_day"]
    if ev is None:
        return pd.DataFrame(columns=cols)
    td = cl.trading_day(pd.DatetimeIndex(ev["decision_time"]))
    first = ~pd.Series(td).duplicated(keep="first").to_numpy()
    out = ev.assign(rr=2.0, first_of_day=first)
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("max1_cisd15_firstofday", lambda: detect(cl.load_m1()))
    print("events", len(ev), "first share", ev["first_of_day"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D", recent="1D")
    res = cl.gate_test(ev, "first_of_day", mask_available_at="decision_time",
                       max_hold=HOLD, claim="+")
    print({k: res.get(k) for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "verdict", "verdict_detail", "ties", "exposure_bars",
                                   "ctrl_overlap")})
    op = {"rules": [
        "baseline: 15m CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming "
        "bar close, enter next M1 open, stop at the protected swing, target 2R, exit at 150min",
        "gate first_of_day: the event is the first 15m CISD decision of its trading day "
        "(18:00 NY roll); later same-day signals are the complement (what the cap skips)"],
        "params": {"tf": "15min", "rr": 2.0, "max_hold": HOLD, "day_open_hour": 18,
                   "cap": 1}}
    src = {"tf": "corpus: concept timeframes ltf 15m (and phase3 4H/15m entry TF)",
           "rr": "corpus: concept rule 'exit at 2R or -1R; do not manage'",
           "max_hold": PHASE3_SRC + " (10 entry-TF bars)",
           "day_open_hour": "session_window_fit: settled 18:00 NY roll",
           "cap": "corpus: 'hard cap of one trade per day'"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="The cap's stated justification is psychological (tilt); "
                              "that part is not decidable from OHLC. This tests the only "
                              "market claim it implies: that skipping later signals costs "
                              "nothing / helps, i.e. first-of-day signals are no worse.")
    print("wrote", p)
