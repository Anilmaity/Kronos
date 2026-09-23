"""futures-trading-hours — Futures trading hours 18:00 to 17:00, Sunday to Friday
(TTrades own voice, specified).

The concept is a clock ENVELOPE definition ("Futures run from 6:00 p.m. to 5:00 p.m.",
"there is no Futures Trading on Saturday", dtsrR8dX2Ro). It makes no directional,
level, timing or outcome claim that a trade, gate or rate test could confirm or refute;
its only measurable is a bar-count sanity check on a data series. That check is a data
property, not a market edge, and it is already settled for this venue: the XAU_USD daily
break resumes at 18:00 NY on 99.8% of 605 occasions under DST-aware Eastern
(session_window_fit; concept_lab rolls the day at 18:00 NY on that basis). The venue is
OANDA spot gold (a CFD), not a futures contract, so the concept's precondition
('instrument is a futures contract') is not met by the data either.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl   # noqa: E402

if __name__ == "__main__":
    p = cl.write_untestable(
        "futures-trading-hours",
        "definitional clock envelope (18:00-17:00 NY, Sun-Fri) with no predictive or trading "
        "claim; its only measurable is a data bar-count sanity check, already settled for this "
        "venue (daily break resumes 18:00 NY on 99.8% of 605 halts, session_window_fit) and "
        "used as the harness's day roll; the data is spot XAU_USD, not a futures contract",
        script=__file__,
        notes="Not a market hypothesis; nothing to reject. The 18:00 anchor it supplies is "
              "consumed by every day-based test in this batch.")
    print(p)
