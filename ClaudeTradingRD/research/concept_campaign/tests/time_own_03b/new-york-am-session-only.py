"""new-york-am-session-only (TTrades own voice): 'move us to New York am session as that is
what I trade' / 'I do not trade the afternoon session' / overnight 'I don't really mess with'.

Gate test on a baseline book (claim '+': participating only in NY AM beats the rest).
  baseline : phase-3 bare 15m CISD (entry TF from the concept's ltf list 15m/5m/1m; 15m is
             the phase-3 primary-stack entry TF), 2R, stop at protected swing, 150min hold.
  gate     : decision time in NY AM 08:30-12:00 New York (DST-aware) -- the ONLY session
             window in his own voice (method_spec §2.5 daily-profile-session-windows;
             session_window_fit '08:30-12:00 (attested quote)').
  complement: every other hour (afternoon, overnight/Asia and London) -- i.e. what the
             rule excludes from participation.
Declared before the run.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params

TF = "15min"
WIN = ("08:30", "12:00")


def detect(m1):
    ev = cisd_book(m1, TF)
    ev["in_ny_am"] = cl.in_window(ev["decision_time"], *WIN)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("t03b_nyam_cisd15_0830_1200", lambda: detect(cl.load_m1()))
    print(len(ev), "events; gate share", ev["in_ny_am"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "in_ny_am", mask_available_at="decision_time",
                       max_hold="150min", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "ties", "verdict", "verdict_detail"):
        print(k, res.get(k))
    p, s = base_params(TF)
    op = {"rules": ["baseline: phase-3 bare 15m CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming 15m close, enter next M1 open, stop at protected swing, 2R, 150min hold",
                    "gate: decision time inside 08:30-12:00 New York (DST-aware) = the NY a.m. participation window",
                    "complement: all other hours (the afternoon and overnight sessions he excludes, plus London)"],
          "params": {**p, "window": "08:30-12:00 NY"}}
    src = {**s, "window": "method_spec §2.5: 'New York a.m. 08:30-12:00' (daily-profile-session-windows, his own voice); session_window_fit '08:30-12:00 (attested quote)'"}
    out = cl.write_result("new-york-am-session-only", None, res, operationalization=op,
                          params_source=src, script=__file__, probe=probe,
                          notes="The concept unit gives no clock; the only own-voice NY a.m. window in the corpus (08:30-12:00) is used. Phase 2 found 07:00-10:00 negative (t=-3.11) and 08:30-12:00 at -0.010R vs null on 3y; this is the certified-span, matched-control version.")
    print(out)
