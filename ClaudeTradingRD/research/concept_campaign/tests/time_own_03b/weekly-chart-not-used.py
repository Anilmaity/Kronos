"""weekly-chart-not-used (TTrades own voice): 'I don't really use the weekly chart' /
'I use the daily and hourly'. Declared before any run.

The level half ('previous week's high/low is the corresponding daily swing') is arithmetic:
PWH/PWL are by construction the max/min of that week's daily highs/lows on the same 18:00
roll, so there is nothing to test there. The decidable half is that the weekly step adds
nothing to a daily+hourly read.

Gate test (claim '+' = the weekly candle adds value; the concept PREDICTS NULL, and a
positive EDGE would refute it):
  population: phase-3 bare 1h CISD (hourly), kept only when aligned with the daily bias =
              prior trading day's candle direction (close vs open, 18:00 roll).
  gate      : also aligned with the prior completed WEEK's candle direction.
  complement: daily-aligned but against the prior week's candle.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params

TF = "1h"


def detect(m1):
    ev = cisd_book(m1, TF)
    t = pd.DatetimeIndex(ev["decision_time"])
    d = cl.prior_hilo(t, "1D", m1=m1)
    w = cl.prior_hilo(t, "1W", m1=m1)
    db = np.sign(d["close"].to_numpy(float) - d["open"].to_numpy(float))
    wb = np.sign(w["close"].to_numpy(float) - w["open"].to_numpy(float))
    ok = np.isfinite(db) & np.isfinite(wb) & (db != 0) & (wb != 0)
    ev = ev[ok & (ev["direction"].to_numpy() == np.nan_to_num(db))].copy()
    t2 = pd.DatetimeIndex(ev["decision_time"])
    w2 = cl.prior_hilo(t2, "1W", m1=m1)
    ev["weekly_aligned"] = ev["direction"].to_numpy() == np.sign(w2["close"].to_numpy(float) - w2["open"].to_numpy(float))
    return ev.reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("t03b_weekly_cisd1h_v1", lambda: detect(cl.load_m1()))
    print(len(ev), "weekly-aligned share", ev["weekly_aligned"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.gate_test(ev, "weekly_aligned", mask_available_at="decision_time", max_hold="10h", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    p, s = base_params(TF)
    op = {"rules": ["population: phase-3 bare 1h CISD (series_open, 2/2, max_wait 3; stop protected swing; 2R; 10h hold) aligned with the prior trading day's candle direction",
                    "gate: also aligned with the prior completed week's candle direction (weekly bias)",
                    "complement: daily-aligned, against the prior week's candle"],
          "params": {**p, "daily_bias": "prior-day candle close vs open", "weekly_bias": "prior-week candle close vs open", "day_open_hour": 18}}
    src = {**s, "daily_bias": "declared-before-run: method_spec §2.4 previous-candle daily bias; corpus yNgx9OAefuI 'I use the daily and hourly'",
           "weekly_bias": "corpus: NESSCPMzWR0 'I don't really use the weekly chart' (he allows a weekly-candle bias 'you can use it')",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    out = cl.write_result("weekly-chart-not-used", None, res, operationalization=op,
                          params_source=src, script=__file__, probe=probe,
                          notes="Claim '+' is the weekly step ADDING value; the concept predicts NULL. NULL is consistent with skipping the weekly chart; EDGE would refute it; NEGATIVE would mean weekly-aligned trades are worse. The PWH/PWL-equals-daily-swing clause is arithmetic identity, not tested.")
    print(out)
