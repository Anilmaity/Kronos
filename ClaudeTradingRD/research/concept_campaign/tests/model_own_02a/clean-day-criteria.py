"""clean-day-criteria — trade test of the four-part 'clean day' checklist (D / 4H / 15m).

  1. Daily candle is a C3 in the anticipated direction: the previous (closed) daily candle
     is a C2 closure in that direction (method_spec §3.2 test).
  2. The 4H candle in progress is a C4 within that daily candle: 4H bar k-2 is a C2 and
     4H bar k-1 is a C3 closure (Reading A, close beyond C2's open, §3.3) in the same
     direction, and bar k starts inside the current trading day.
  3. The aligned timeframes have not already expanded — declared-before-run: the day's
     objective (the C2 day's extreme = previous day high for bull / low for bear, §3.3 /
     execution.targets 'previous day high/low') has not been traded to yet at the decision.
  4. A reversal has formed on the execution timeframe leaving a new protected swing:
     a 15m CISD in the direction, confirmed inside 4H candle k.
Execution: enter next M1 open; stop = the protected swing; target = previous day high/low;
skip if the target is < 2R from the confirming close (§5.3 2R floor); exit at the close of
the daily candle (§5.5 time exit at the HTF candle close). First qualifying setup per day
(§5.5 one-trade-per-day cap).
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from _common import cisd, c2_flags, c3a_flags, in_progress, last_closed, running_in_parent, utc  # noqa: E402

CID = "clean-day-criteria"
MIN_RR = 2.0


def detect(m1):
    b15 = cl.build_bars(m1, "15min")
    b4 = cl.build_bars(m1, "4h", grid4h="forex")
    bd = cl.build_bars(m1, "1D")
    ev = cisd(b15, max_wait=3)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    t = ev["decision_time"]
    d = ev["direction"].to_numpy()
    px = ev["confirm_close"].to_numpy()
    stop = ev["stop_px"].to_numpy()
    # 1. day is a C3: previous daily bar is a C2 in direction
    pday = in_progress(bd, t)
    ok = pday >= 2
    pc = np.clip(pday, 1, None)
    bull_d, bear_d = c2_flags(bd)
    ok &= np.where(d > 0, bull_d[pc - 1], bear_d[pc - 1])
    # 2. 4H candle in progress is a C4 (k-1 is a C3-A closure after a C2 at k-2)
    # (kp = last CLOSED 4H bar; the entry trades inside the candle after it)
    kp = last_closed(b4, t)
    ok &= kp >= 2
    kc = np.clip(kp, 0, None)
    c3b, c3s = c3a_flags(b4)
    ok &= np.where(d > 0, c3b[kc], c3s[kc])
    day_start = utc(bd.index)[pc].asi8 if len(bd) else np.array([])
    ok &= utc(b4["close_time"].to_numpy())[kc].asi8 >= day_start   # candle k opens today
    # 3. not already expanded: the day's objective (prev day extreme) not yet taken
    tgt = np.where(d > 0, bd["high"].to_numpy()[pc - 1], bd["low"].to_numpy()[pc - 1])
    j = b15.index.get_indexer(ev["confirm_start"])
    rs = running_in_parent(b15, bd)
    ok &= np.where(d > 0, rs["run_hi"].to_numpy()[j] < tgt, rs["run_lo"].to_numpy()[j] > tgt)
    # 4. 15m CISD in direction (the event itself); 2R floor to the objective
    risk = np.where(d > 0, px - stop, stop - px)
    rew = np.where(d > 0, tgt - px, px - tgt)
    ok &= (risk > 0) & (rew >= MIN_RR * risk)
    day_close = utc(bd["close_time"].to_numpy())[pc]
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": stop, "target_px": tgt,
                        "max_hold": pd.Series(day_close - utc(t)).to_numpy(),
                        "_day": pday})[ok]
    out = out.sort_values("decision_time").drop_duplicates("_day", keep="first")
    return out.drop(columns="_day").reset_index(drop=True)


def main():
    ev = cl.cache_frame("clean_day_v2", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev)
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                    "verdict_detail", "exposure_bars", "ties")})
    op = {"rules": [
        "daily = 18:00 NY trading day; 4H = forex grid; execution = UTC-aligned 15m bars",
        "1. previous closed daily candle is a C2 closure in the direction (bull: low<prev low "
        "& close>prev low; mirror) -> today is candle 3",
        "2. the 4H candle in progress (starting inside today) is a C4: 4H k-2 is a C2 and 4H "
        "k-1 closes beyond k-2's open in the direction (C3 Reading A)",
        "3. not already expanded: the day's running high (bull) is still below the previous "
        "day high = the C2 day's extreme / the day's objective (mirror bear)",
        "4. a 15m CISD (series_open, 2/2 swing, max_wait 3) in the direction confirms inside "
        "that 4H candle -> new protected swing",
        "enter next M1 open; stop = protected swing; target = previous day high/low; require "
        "target >= 2R from the confirming close; hold to the daily candle close; first "
        "qualifying setup per trading day"],
        "params": {"exec_tf": "15min", "level_rule": "series_open", "max_wait": 3,
                   "swing": "2/2", "c3_reading": "A (close beyond C2 open)",
                   "not_expanded": "prev-day extreme untouched", "min_rr": MIN_RR,
                   "max_hold": "to daily close", "one_per_day": True, "grid4h": "forex",
                   "day_open_hour": 18}}
    src = {"exec_tf": "corpus: i2HhHhWdaPQ 'Trade a C3 on the daily. Trade the C4 on the "
                      "4hour.' (daily / 4-hour / 15-minute stack)",
           "level_rule": "method_spec: §4.2 first-candle-open default",
           "max_wait": "phase3: locked config max_wait=3 (§4.2 1-3 candles)",
           "swing": "method_spec: §1.1 three-candle fractal; phase3 2/2",
           "c3_reading": "method_spec: §3.3 Reading A (this unit's Shorts)",
           "not_expanded": "declared-before-run: the day's objective (previous-day extreme, "
                           "concept execution.targets) not yet reached = move not spent",
           "min_rr": "method_spec: §5.3 2R is the floor; skip if not reachable",
           "max_hold": "method_spec: §5.5 time-based exit at the HTF candle close",
           "one_per_day": "method_spec: §5.5 one trade per day cap",
           "grid4h": "session_window_fit: forex grid for gold",
           "day_open_hour": "method_spec: §1.4 18:00 canon"}
    path = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                           script=__file__, probe=probe,
                           notes="trade_test vs matched random entries (same stop/target "
                                 "distance, same per-row hold). BUG FIX + ONE RE-RUN: the first "
                                 "run (n=171, diff +0.469R [+0.138,+0.840], UNDERPOWERED) located "
                                 "the 4H/daily candle with start < t <= close, so a CISD closing "
                                 "exactly at a 4H close was checked against the candle that had "
                                 "just ended rather than the one the entry trades inside. Fixed to "
                                 "the candle AFTER the last closed 4H bar (the one the entry trades inside) and re-run once; the fix also had to avoid requiring that candle's bar to exist yet (probe).")
    print("wrote", path)


if __name__ == "__main__":
    main()
