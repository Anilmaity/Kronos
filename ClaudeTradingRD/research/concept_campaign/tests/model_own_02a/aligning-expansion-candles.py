"""aligning-expansion-candles — gate test on the 15m bare-CISD book.

Claim (+): 15m continuation entries taken when the higher-timeframe candles are aligned
for expansion in the trade's direction beat entries taken without that alignment.

Baseline book (stated): phase-3 rung-0 on 15m — CISD series_open, 2/2 swing, max_wait 3,
enter next M1 open after the confirming close, stop = protected swing, 2R, 150min.
The model's execution row says exactly this: 'protected swing / continuation entry on the
lowest aligned timeframe; stop on that protected swing; 2R'.

Two readings of 'aligned' (the concept is contested):
  a  CANDLE-3 STACK — "a daily candle 3, a 4-hour candle 3 ... by definition just a
     trend". The in-progress daily AND in-progress 4H candles are each the candle after
     a C2 closure in the trade direction (last CLOSED daily and last CLOSED 4H bar are C2s).
     Two layers (D + 4H) = the stated minimum for 15m execution.
  b  LIVE EXPANSION SUPPORT — each layer's current candle "supports expansion": at the
     decision it trades beyond its own open in the trade direction AND its opposing run
     (open -> extreme against the direction, §3.6) is <= 1.0 x its body so far
     (threshold_fits grade-A default wick/body 1.0). D + 4H both required.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from _common import cisd, c2_flags, last_closed, running_in_parent  # noqa: E402

CID = "aligning-expansion-candles"
WICK_BODY_CUT = 1.0


def detect(m1):
    b15 = cl.build_bars(m1, "15min")
    b4 = cl.build_bars(m1, "4h", grid4h="forex")
    bd = cl.build_bars(m1, "1D")
    ev = cisd(b15, max_wait=3)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "c3_stack", "exp_support"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    t = ev["decision_time"]
    d = ev["direction"].to_numpy()
    # reading a: last CLOSED daily / 4H bar is a C2 in the trade direction
    ok = np.ones(len(ev), bool)
    stack = np.ones(len(ev), bool)
    for bars_ in (bd, b4):
        bull, bear = c2_flags(bars_)
        p = last_closed(bars_, t)
        ok &= p >= 1
        pc = np.clip(p, 0, None)
        stack &= np.where(d > 0, bull[pc], bear[pc])
    # reading b: in-progress D and 4H candles support expansion at the decision
    sup = np.ones(len(ev), bool)
    j = b15.index.get_indexer(ev["confirm_start"])
    px = ev["confirm_close"].to_numpy()
    for par in (bd, b4):
        rs = running_in_parent(b15, par)
        o = rs["p_open"].to_numpy()[j]
        body = np.where(d > 0, px - o, o - px)
        opp = np.where(d > 0, o - rs["run_lo"].to_numpy()[j], rs["run_hi"].to_numpy()[j] - o)
        ok &= rs["parent"].to_numpy()[j] >= 0
        sup &= (body > 0) & (opp <= WICK_BODY_CUT * body)
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": ev["stop_px"].to_numpy(), "rr": 2.0,
                        "c3_stack": stack, "exp_support": sup})
    return out[ok].reset_index(drop=True)


def main():
    ev = cl.cache_frame("aec_15m_cisd_mw3_gates_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev[["c3_stack", "exp_support"]].mean().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    base_rules = ["baseline: 15m CISD (series_open, 2/2 swing, max_wait 3) on UTC-aligned 15m "
                  "bars; decide at confirming bar close; enter next M1 open; stop at protected "
                  "swing; 2R target; 150min max hold",
                  "daily = 18:00 NY trading day; 4H = forex grid"]
    common_params = {"baseline_tf": "15min", "level_rule": "series_open", "swing": "2/2",
                     "max_wait": 3, "rr": 2.0, "max_hold": "150min", "grid4h": "forex",
                     "day_open_hour": 18}
    common_src = {"baseline_tf": "corpus: Kf4c41_qO1s 'two expansion candles aligned' "
                                 "(daily + 4-hour is enough to execute on the 15-minute)",
                  "level_rule": "method_spec: §4.2 carry first-candle-open as the default",
                  "swing": "phase3: locked config §1.8-1.13",
                  "max_wait": "phase3: locked config max_wait=3",
                  "rr": "method_spec: §5.3 2R; concept execution.targets '2R'",
                  "max_hold": "phase3: 10 entry-TF bars (§1.13)",
                  "grid4h": "session_window_fit: forex grid for gold",
                  "day_open_hour": "method_spec: §1.4 18:00 daily open is canon"}
    readings = {
        "a": ("c3_stack",
              ["gate: last CLOSED daily candle is a C2 closure in the trade direction AND last "
               "CLOSED 4H candle is a C2 closure in the trade direction (so the in-progress "
               "daily and 4H candles are both candle 3)",
               "C2 bull: low<prev low & close>prev low (mirror bear) — method_spec §3.2"],
              {"layers": "D+4H"},
              {"layers": "corpus: TL704EemfdA 'a daily candle three, a 4-hour candle three' "
                         "+ Kf4c41_qO1s minimum two aligned for 15m execution"}),
        "b": ("exp_support",
              ["gate: in-progress daily AND in-progress 4H candle each trade beyond their open "
               "in the trade direction at the decision, with opposing run (open->extreme "
               "against direction) <= 1.0 x body so far",
               "running extremes from 15m bars closed by the decision"],
              {"layers": "D+4H", "wick_body_cut": WICK_BODY_CUT},
              {"layers": "corpus: Kf4c41_qO1s minimum two aligned expansion candles",
               "wick_body_cut": "threshold_fits: small wick default opposing_run/body <= 1.0 "
                                "(grade A)"}),
    }
    for rd, (col, rules_, p_, s_) in readings.items():
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold="150min")
        print(rd, {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                            "verdict_detail")}, res.get("gate"))
        path = cl.write_result(
            CID, rd, res,
            operationalization={"rules": base_rules + rules_, "params": {**common_params, **p_}},
            params_source={**common_src, **s_}, script=__file__, probe=probe,
            notes="gate_test vs complement of the same 15m CISD book; claim '+'. "
                  "mask_available_at = decision time (gate reads only bars closed by then).")
        print("wrote", path)


if __name__ == "__main__":
    main()
