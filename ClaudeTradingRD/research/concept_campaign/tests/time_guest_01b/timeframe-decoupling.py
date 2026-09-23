"""timeframe-decoupling (Alex's Options, guest).

Claim: at the session open the day/1h/30/15/5 candles share one open, so lower-timeframe
signals carry no independent information until their timeframes have decoupled (the 60m
is last, one hour after the open). Lower-timeframe signals taken after decoupling are
better than those taken while still coupled.

Session open for gold = the trading-day open, 18:00 NY (the only moment at which the day,
hour, 30, 15 and 5 all share one opening price on this venue).
Test: gate_test on the phase-3 locked bare 5m CISD book (5m is the concept's own
'first fiver' unit). gated = decided after the hour has decoupled (decision more than 60
minutes after the day open); complement = decided within the first 60 minutes
(18:00 < decision <= 19:00 NY). Claim '+'.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params


def detect(m1):
    ev = cisd_book(m1, "5min")
    if ev.empty:
        ev["decoupled"] = pd.Series(dtype=bool)
        return ev
    mod = cl.ny_minute_of_day(pd.DatetimeIndex(ev["decision_time"]))
    coupled = (mod > 18 * 60) & (mod <= 19 * 60)
    ev["decoupled"] = ~coupled
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("tg01b_decouple_5mcisd", lambda: detect(cl.load_m1()))
    print(len(ev), "events; coupled share", 1 - ev["decoupled"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "decoupled", mask_available_at="decision_time", max_hold="50min", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    bp, bs = base_params("5min", "50min")
    op = {"rules": ["baseline: phase-3 bare 5m CISD (series_open, swing 2/2, max_wait 3), decide at confirming 5m close, enter next M1 open, stop protected swing, 2R, 50min (10 bars)",
                    "session open = 18:00 NY trading-day open (day/1h/30/15/5 share one open)",
                    "complement (coupled) = decision in (18:00, 19:00] NY, before the 60m has decoupled",
                    "gated (decoupled) = every other decision"],
          "params": {**bp, "session_open": "18:00 NY", "coupled_window_min": 60}}
    src = {**bs,
           "session_open": "session_window_fit: 18:00 NY day roll (settled); the concept's RTH open has no gold equivalent other than the day open",
           "coupled_window_min": "corpus: 1XWyy6Q-_8Q 'the first hour of the day the hour and day open are the same' - 60m is the last to decouple"}
    p = cl.write_result("timeframe-decoupling", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="18:00 NY reopen hour is also a post-halt gap period (session_window_fit); the complement therefore mixes decoupling with reopen conditions.")
    print(p)
