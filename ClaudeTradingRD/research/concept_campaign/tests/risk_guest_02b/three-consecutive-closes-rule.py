"""three-consecutive-closes-rule (Jokerszn, guest): after three consecutive same-direction
daily closes, take no trades in that direction on the fourth day.

Gate on the baseline 1h CISD book. mask `allowed` = NOT (the last 3 completed daily candles
all closed in the trade's direction). claim '+': allowed trades beat blocked ones.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, BASE_PARAMS, BASE_SRC, BASE_RULE

RUN_LEN = 3


def detect(m1):
    ev = cisd_book(m1)
    d = cl.build_bars(m1, "1D")
    sgn = np.sign(d["close"].to_numpy() - d["open"].to_numpy())
    run = np.zeros(len(d), dtype=int)
    for i in range(len(d)):
        if sgn[i] == 0:
            run[i] = 0
        elif i > 0 and sgn[i] == sgn[i - 1] and run[i - 1] > 0:
            run[i] = run[i - 1] + 1
        else:
            run[i] = 1
    d = d.assign(run=run, sgn=sgn)
    a = cl.asof(d, ev["decision_time"])
    run_a = a["run"].to_numpy(float)
    sgn_a = a["sgn"].to_numpy(float)
    blocked = (run_a >= RUN_LEN) & (sgn_a == ev["direction"].to_numpy())
    ev["allowed"] = ~blocked
    ev["gate_at"] = pd.DatetimeIndex(a["close_time"]).where(~pd.isna(a["close_time"]),
                                                            ev["decision_time"])
    ev = ev[~np.isnan(run_a)].reset_index(drop=True)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("rg02b_3closes_1hcisd", lambda: detect(cl.load_m1()))
    print(len(ev), "events; allowed share", ev["allowed"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "allowed", mask_available_at="gate_at", max_hold="10h", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [BASE_RULE,
                    "daily candles: 18:00 NY trading days built from M1; direction = sign(close-open)",
                    "run = count of consecutive same-direction completed daily candles ending at the last completed day",
                    "blocked = run >= 3 and the trade direction equals the run direction (trade is on day 4+); allowed = the rest",
                    "counter-direction trades on day 4 stay allowed (the concept's example implies they are)"],
          "params": {**BASE_PARAMS, "run_len": RUN_LEN, "close_direction": "close vs open",
                     "day_open_hour": 18}}
    src = {**BASE_SRC,
           "run_len": "corpus: JABOO4LYNjQ (three consecutive daily closes, no trades that direction on day four)",
           "close_direction": "declared-before-run: 'candle closing in the same direction' read as bullish/bearish candle body",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result("three-consecutive-closes-rule", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="gate mask known at the close of the third daily candle (gate_at).")
    print(p)
