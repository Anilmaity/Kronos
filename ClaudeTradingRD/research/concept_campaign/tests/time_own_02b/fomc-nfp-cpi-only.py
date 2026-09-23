"""fomc-nfp-cpi-only (specified, own voice): 'never trade after FOMC. I just wait for the next day'.

The one executable rule in the concept is the post-FOMC block. Gate on the phase-3 bare 15m
CISD book (hold 150 min), claim '+' = allowed beats blocked (control-adjusted):
  blocked = decision on an FOMC statement session date (NY, 18:00 roll) at or after 14:00 NY
            (statement time) -- i.e. the rest of that session; trading resumes at the next
            session (18:00 NY reopen).
  allowed = everything else.
FOMC scheduled statement dates are declared in _common.py before any run. The 'track only
three releases' half is a calendar-reading preference with no outcome of its own, and the
'expect a range-bound FOMC morning' remark is not a trading rule; neither is scored here.
CPI does not enter this rule (only the FOMC clause blocks anything).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params, base_rule, summarize, FOMC

TF = "15min"


def detect(m1):
    ev = cisd_book(m1, TF)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    sd = pd.DatetimeIndex(cl.session_date(t)).tz_localize(None).normalize()
    is_fomc = np.asarray(sd.isin(FOMC))
    mod = cl.ny_minute_of_day(t)
    after = (mod >= 14 * 60) & (mod < 18 * 60)
    ev["allowed"] = ~(is_fomc & after)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"to02b_fomc_after_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), "events; blocked", int((~ev["allowed"]).sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.gate_test(ev, "allowed", mask_available_at="decision_time", max_hold="150min", claim="+")
    summarize(res)
    bp, bs = base_params(TF)
    params = {**bp, "fomc_calendar": "scheduled FOMC statement dates 2016-01..2026-03 (81 dates, no emergency actions)",
              "release_time": "14:00 NY", "block_until": "18:00 NY session roll (next session)"}
    src = {**bs,
           "fomc_calendar": "declared-before-run: public Federal Reserve meeting calendar, typed in _common.py before any run",
           "release_time": "declared-before-run: FOMC statement release time 14:00 ET",
           "block_until": "corpus: xraklBJHW5k 'never trade after FOMC. I just wait for the next day'"}
    rules = [base_rule(TF),
             "blocked = decision on an FOMC statement session date at/after 14:00 NY (rest of that session)",
             "allowed = all other decisions"]
    p = cl.write_result("fomc-nfp-cpi-only", None, res,
                        operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Only ~81 FOMC afternoons exist, so the blocked arm's effective n (trading days) is structurally < 200: this concept cannot reach a powered verdict on 10.5 years. The 'only three releases' calendar preference and the FOMC-morning expectation are not scored.")
    print(p)
