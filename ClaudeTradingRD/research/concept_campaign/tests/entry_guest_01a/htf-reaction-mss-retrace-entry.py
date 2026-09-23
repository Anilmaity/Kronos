"""htf-reaction-mss-retrace-entry — HTF level reached -> LTF structure shift -> retracement
entry into the array left by the shift.  Contested: two readings, both trade_test.

(a) Trader T: 1h fractal swing high/low swept; 5m close through the relative fractal
    extreme that existed PRIOR to the sweep (within 6h); sell/buy limit on the block
    (the latest 5m FVG of the shift leg, near edge); stop = sweep extreme; fixed 2R;
    order abandoned if price runs to the 2R target before filling.
(b) $niper / variant: liquidity taken = previous trading day's high/low; 15m close
    through the latest confirmed swing (MSS) within 6h, same day, with an FVG in the
    leg; limit at the FVG; stop = the extreme that tagged the level; target = the
    opposing previous-day extreme (the opposing pool); missed if the target trades first.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a")
from common01a import cl, trader_t_setups, niper_pdhl_setups  # noqa: E402

HNS = np.int64(3600 * 10 ** 9)
A = dict(htf="1h", ltf="5min", swing=(2, 2), sweep_window_ns=120 * HNS, bos_bars=72, expiry_ns=12 * HNS, rr=2.0)
B = dict(ltf="15min", swing=(2, 2), mss_bars=24, expiry_ns=12 * HNS)
HOLD_A, HOLD_B = "12h", "24h"


def detect_a(m1):
    ev = trader_t_setups(m1, **A)
    return ev[~ev["ran_first"]].reset_index(drop=True)


def detect_b(m1):
    return niper_pdhl_setups(m1, **B)


COMMON_PS = {"ctrl_tod_tol_min": "declared-before-run: 30 (README trap 9)",
             "swing": "declared-before-run: fractal 2/2 on every timeframe"}

if __name__ == "__main__":
    # ── reading a ──
    ev = cl.cache_frame("htf_mss_a_traderT_1h5m_v1", lambda: detect_a(cl.load_m1()))
    print("a:", len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=HOLD_A, ctrl_tod_tol_min=30)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars", "ties", "avg_R", "win_rate"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "1h fractal swing (2/2) known at the close of bar j+2; sweep = first 5m bar after that trading beyond it (within 5 days); one setup per sweep bar.",
        "Structure reference = latest 5m fractal swing on the opposite side confirmed before the sweep bar (Trader T's 'relative low prior to the sweep').",
        "Break = first 5m CLOSE beyond that reference within 72 bars (6h) from the sweep bar.",
        "Block = the most recent same-direction 5m FVG stamped between the sweep bar and the break bar; no FVG -> no setup. Limit at its near edge.",
        "Stop = sweep extreme (max high / min low from sweep bar to break bar); target = 2R from the limit.",
        "Order live 12h from the break close; fill = first M1 bar through the limit; ABANDONED if the 2R target price traded on an earlier M1 bar (Trader T's rule)."],
        "params": {**{k: (str(v) if isinstance(v, np.integer) else v) for k, v in A.items()},
                   "sweep_window": "5D", "expiry": "12h", "max_hold": HOLD_A, "ctrl_tod_tol_min": 30}}
    ps = {**COMMON_PS,
          "htf": "corpus: wCtxmWe4KNc 'when the market comes up it sweeps the high I then go to the smaller time frame like the five minute' (hourly sweep per concept yaml)",
          "ltf": "corpus: wCtxmWe4KNc 'I just wait for a break and structure on the five minutes'",
          "structure_ref": "corpus: wCtxmWe4KNc 'I use the relative low prior to the sweep'",
          "rr": "corpus: wCtxmWe4KNc 'I just took a simple 2R'",
          "cancel_rule": "corpus: wCtxmWe4KNc 'once it runs to my target without fill I usually um I do remove'",
          "block": "declared-before-run: the block = latest 5m FVG of the shift leg (Trader T's 'block' undefined; $niper prefers the FVG)",
          "stop": "corpus-derived: execution 'Beyond the swing that produced the break' / variant 'stop rests at the extreme that tagged the HTF level'",
          "sweep_window_ns": "declared-before-run: 5 days", "sweep_window": "declared-before-run: 5 days",
          "expiry": "declared-before-run: 12h", "bos_bars": "declared-before-run: 72 5m bars (6h)",
          "expiry_ns": "declared-before-run: 12h", "max_hold": "declared-before-run: 12h"}
    print(cl.write_result("htf-reaction-mss-retrace-entry", "a", res, operationalization=op, params_source=ps,
                          script=__file__, probe=probe,
                          notes="Script re-executed once after a params_source key typo made write_result refuse; the test itself is deterministic and unchanged."))

    # ── reading b ──
    ev = cl.cache_frame("htf_mss_b_niper_pdhl_15m_v1", lambda: detect_b(cl.load_m1()))
    print("b:", len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=HOLD_B, ctrl_tod_tol_min=30)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars", "ties", "avg_R", "win_rate"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "Trading day rolls 18:00 NY. Liquidity taken = first 15m bar of the day trading beyond the previous trading day's high (short) / low (long).",
        "MSS = first 15m CLOSE beyond the latest confirmed 15m fractal swing (2/2, known by the prior bar's close) on the other side, within 24 bars (6h) of the sweep bar and the same trading day.",
        "The MSS leg must leave a same-direction 15m FVG (stamped between the sweep bar and the MSS bar); latest one used; limit at its near edge.",
        "Stop = the extreme that tagged the level (max high / min low sweep bar..MSS bar); target = previous day's opposite extreme; it must lie beyond the limit.",
        "Order live 12h from the MSS close; fill = first M1 through the limit; MISSED (no trade) if the target traded first.",
        "No premium/discount gate here (tested as discount-requirement-before-entry)."],
        "params": {**{k: (str(v) if isinstance(v, np.integer) else v) for k, v in B.items()},
                   "expiry": "12h", "max_hold": HOLD_B, "ctrl_tod_tol_min": 30}}
    ps = {**COMMON_PS,
          "htf_level": "corpus: UmLWRlXd_V8 precondition 'liquidity has been taken (previous daily high, previous weekly high)'",
          "ltf": "corpus: UmLWRlXd_V8 'drop to the 15-minute or the hourly' -> 15m",
          "mss": "corpus: UmLWRlXd_V8 'I need a market structure break for a shift'",
          "entry_array": "corpus: UmLWRlXd_V8 '$niper prefers a fair value gap, then an order block' -> FVG",
          "target": "corpus: concept execution targets 'previous daily low or high'",
          "stop": "corpus: variant 'the stop rests at the extreme that tagged the higher-timeframe level'",
          "missed_rule": "corpus: discount-requirement invalidation 'Price expands to the objective without returning ... the trade is missed, not taken late'",
          "mss_bars": "declared-before-run: 24 15m bars (6h), same trading day",
          "expiry": "declared-before-run: 12h",
          "expiry_ns": "declared-before-run: 12h", "max_hold": "declared-before-run: 24h"}
    print(cl.write_result("htf-reaction-mss-retrace-entry", "b", res, operationalization=op, params_source=ps,
                          script=__file__, probe=probe))
