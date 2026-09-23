"""opening-time-only-execution (contested guest concept: Ash Trades, $niper, AM Trades, DTR).

"Execute only at / after a session open" -- the speakers disagree on which window,
so two readings, declared before any run. Both are gate_tests, claim '+', on the same
baseline book: bare 5m CISD, phase-3 locked config (series_open level, 2/2 swings,
max_wait 3), decide at the confirming 5m close, next M1 open, stop at the protected
swing, 2R, hold 10 bars = 50 min. (5m = Ash's entry-function frame, inside the
concept's listed LTFs 15m/5m/1m.)

  a  Ash Trades: only at an opening time -- London open 02:00 NY or New York open
     09:30 NY. Ash sets no maximum delay; declared 60 minutes: pass = decision in
     [02:00, 03:00) or [09:30, 10:30) NY; complement = every other decision.
  b  $niper + AM Trades: nothing before the 09:30 equities open, nothing in the PM
     session. AM's session end is not given; the method spec's NY AM window ends
     12:00. pass = decision in [09:30, 12:00) NY; complement = every other decision.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import PHASE3_CISD, cl, detect_cisd, pd, show  # noqa: E402

CID = "opening-time-only-execution"
TF = "5min"
MAX_HOLD = "50min"
A_WINDOWS = (("02:00", "03:00"), ("09:30", "10:30"))
B_WINDOW = ("09:30", "12:00")


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    ev = detect_cisd(m1, TF)
    if ev.empty:
        return ev.assign(at_open=pd.Series(dtype=bool), ny_am=pd.Series(dtype=bool))
    t = ev["decision_time"]
    ev["at_open"] = cl.in_window(t, *A_WINDOWS[0]) | cl.in_window(t, *A_WINDOWS[1])
    ev["ny_am"] = cl.in_window(t, *B_WINDOW)
    return ev


BASE_RULE = ("baseline: bare 5m CISD (series_open level, 2/2 swings, max_wait 3), decide at the confirming "
             "5m close, enter next M1 open, stop at the protected swing, 2R, hold 50 min")
BASE_PARAMS = {"tf": TF, "max_hold": MAX_HOLD, "level_rule": "series_open", "swing": "2/2",
               "max_wait": 3, "rr": 2.0}
BASE_SRC = {"tf": "corpus: zXtJSSkiNmo Ash chain daily -> hourly -> 5-minute entry function (concepts yaml timeframe-alignment-ladder); within this yaml's ltf 15m/5m/1m",
            "max_hold": PHASE3_CISD, "level_rule": PHASE3_CISD, "swing": PHASE3_CISD,
            "max_wait": PHASE3_CISD, "rr": PHASE3_CISD}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_cisd5_v1", lambda: detect(cl.load_m1()))
    print("n", len(ev), "at_open", ev["at_open"].mean(), "ny_am", ev["ny_am"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        res = cl.gate_test(ev, "at_open", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="+")
        show(res)
        op = {"rules": [BASE_RULE,
                        "gate (pass) = decision within 60 min after the London open 02:00 NY or the NY open "
                        "09:30 NY; complement = all other decisions",
                        "claim '+': setups at an opening time beat the rest"],
              "params": {**BASE_PARAMS, "windows": [list(w) for w in A_WINDOWS], "max_delay_min": 60}}
        src = {**BASE_SRC,
               "windows": "corpus: zXtJSSkiNmo Ash 'the only trade taken is at an opening time - London open 02:00 "
                          "EST or New York open 09:30' (concept yaml detection_rules)",
               "max_delay_min": "declared-before-run: Ash sets no maximum delay; one hour after each open"}
        p = cl.write_result(CID, "a", res, operationalization=op, params_source=src, script=__file__,
                            probe=probe, notes="Reading a = Ash Trades' two opening times. Gold, not indices.")
        print("wrote", p)
    if "b" in which:
        res = cl.gate_test(ev, "ny_am", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="+")
        show(res)
        op = {"rules": [BASE_RULE,
                        "gate (pass) = decision in [09:30, 12:00) NY (no pre-09:30 execution, no PM session); "
                        "complement = all other decisions",
                        "claim '+': NY-AM-after-the-open setups beat the rest"],
              "params": {**BASE_PARAMS, "window": list(B_WINDOW)}}
        src = {**BASE_SRC,
               "window": "corpus: 5aRB_ZY3474 $niper 'no execution before the 09:30 equities open' + QmGJFxfSHxM AM "
                         "Trades PM ignored; end 12:00 = session_window_fit SESSION_WINDOWS ny_am end"}
        p = cl.write_result(CID, "b", res, operationalization=op, params_source=src, script=__file__,
                            probe=probe, notes="Reading b = $niper's post-09:30 rule combined with AM Trades' "
                            "AM-only rule. Gold, not indices ($niper applies it to indices).")
        print("wrote", p)
