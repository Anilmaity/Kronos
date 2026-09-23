"""four-am-analysis-start (guest: Day Trading Rauf, qFtfD09Vv3E).

"I usually start my day from 4am so I don't really consider any price action before
4am to be any significant ... I don't really like to trade London session."

Measurable (concept yaml): "outcome of a fixed model run on pre-04:00 vs post-04:00
setups". gate_test, claim '+', declared before the run:
  baseline  bare 5m CISD, phase-3 locked config (series_open level, 2/2 swings,
            max_wait 3), decide at the confirming 5m close, next M1 open, stop at the
            protected swing, 2R, hold 10 bars = 50 min. 5m because the concept's LTFs
            are 1H/5m/1m and 5m is his stated execution frame elsewhere in the stream.
  gate      decision in [04:00, 17:00) NY (his day) vs complement [18:00, 04:00) NY
            (the trading day's pre-04:00 hours: Asia + early London).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import PHASE3_CISD, cl, detect_cisd, pd, show  # noqa: E402

CID = "four-am-analysis-start"
TF = "5min"
MAX_HOLD = "50min"
DAY_START, DAY_END = "04:00", "17:00"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    ev = detect_cisd(m1, TF)
    if ev.empty:
        return ev.assign(after_4am=pd.Series(dtype=bool))
    ev["after_4am"] = cl.in_window(ev["decision_time"], DAY_START, DAY_END)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_cisd5_v1", lambda: detect(cl.load_m1()))
    print("n", len(ev), "after share", ev["after_4am"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    res = cl.gate_test(ev, "after_4am", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="+")
    show(res)
    op = {"rules": [
        "baseline: bare 5m CISD (series_open level, 2/2 swings, max_wait 3), decide at the confirming 5m close, "
        "enter next M1 open, stop at the protected swing, 2R, hold 50 min",
        "gate (pass) = decision at/after 04:00 and before 17:00 NY; complement = 18:00-04:00 NY "
        "(the part of the trading day he discards, incl. the London open)",
        "claim '+': setups from 04:00 on beat setups before 04:00"],
        "params": {"tf": TF, "max_hold": MAX_HOLD, "day_start": DAY_START, "day_end": DAY_END,
                   "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": 2.0}}
    src = {"tf": "corpus: concept yaml timeframes.ltf lists 1H/5m/1m (qFtfD09Vv3E); 5m = middle of the listed LTFs",
           "max_hold": PHASE3_CISD, "level_rule": PHASE3_CISD, "swing": PHASE3_CISD,
           "max_wait": PHASE3_CISD, "rr": PHASE3_CISD,
           "day_start": "corpus: qFtfD09Vv3E 'I usually start my day from 4am' (EST, per the concept's ambiguity note)",
           "day_end": "session_window_fit: 17:00 NY daily halt / 18:00 roll"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="Gold, not indices. The 'NY = continuation or reversal of London' "
                        "framing is a classification with no stated prediction, so only the time-discard rule is scored.")
    print("wrote", p)
