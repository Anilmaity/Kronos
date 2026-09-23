"""macros-not-used — "Macros are fake ... all a macro is is a certain section of an OHLC".

The concept is a REJECTION of ICT macro windows. Its own measurable: "whether
macro-window filtering adds anything on top of an OHLC-shape model on the same trade
set". So the hypothesis tested is the one he rejects — "entries inside a macro window
are better" (claim '+') — and the concept predicts NULL (EDGE would refute him).

Operationalisation (declared before the first run):
  * baseline (the OHLC-shape model): phase-3 rung-0 5m CISD book (series_open, 2/2,
    max_wait 3, min_series 1), restricted to decisions inside the NY a.m. session
    08:30-12:00 so the gate is compared with the same morning, not with Asia.
  * gate: decision time inside a corpus-quoted macro window, 09:20-09:40 or
    09:50-10:10 NY ([start, end)).
  * enter next M1 open, stop protected swing, 2R, hold 50 min (10 bars).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, cisd_book, PHASE3_SRC  # noqa: E402

CID = "macros-not-used"
MACROS = [("09:20", "09:40"), ("09:50", "10:10")]
SESSION = ("08:30", "12:00")


def detect(m1):
    ev = cisd_book(m1, "5min")
    if len(ev) == 0:
        ev["in_macro"] = pd.Series(dtype=bool)
        return ev
    ev = ev[cl.in_window(ev["decision_time"], *SESSION)].reset_index(drop=True)
    m = np.zeros(len(ev), bool)
    for a, b in MACROS:
        m |= cl.in_window(ev["decision_time"], a, b)
    ev["in_macro"] = m
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("cisd5m_nyam_macro", lambda: detect(cl.load_m1()))
    print("events", len(ev), "gated", int(ev["in_macro"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "in_macro", mask_available_at="decision_time",
                       max_hold="50min", claim="+")
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "verdict", "verdict_detail", "ties", "ctrl_overlap",
                                   "halves", "exposure_bars")})
    op = {"rules": [
        "baseline: phase-3 rung-0 5m CISD, decisions inside NY a.m. 08:30-12:00; enter next "
        "M1 open; stop protected swing; 2R; hold 50 min",
        "gate: decision inside a macro window 09:20-09:40 or 09:50-10:10 NY",
        "claim '+' is the ICT macro claim the concept rejects; the concept predicts NULL"],
        "params": {"tf": "5min", "max_hold": "50min", "rr": 2.0,
                   "macros": MACROS, "session": SESSION}}
    src = {"tf": PHASE3_SRC, "max_hold": PHASE3_SRC, "rr": PHASE3_SRC,
           "macros": "corpus: macros-are-htf-opens '9:50 to 10:10'; t_talks_03 study unit "
                     "'he trades the 9:20-9:40 macro'",
           "session": "session_window_fit: NY a.m. 08:30-12:00 (SESSION_WINDOWS ny_am, "
                      "daily-profile window)"}
    print(cl.write_result(CID, None, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Rejection concept: the tested claim is the macro window "
                                "improving the 5m CISD book (ICT view). NULL supports his "
                                "'macros are fake'; EDGE would refute it; NEGATIVE would "
                                "mean macro-window entries are worse."))
