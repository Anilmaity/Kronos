"""pivot-machine-gun (guest: Alex's Options, 1XWyy6Q-_8Q) -> gate_test.

Reading (declared before the run), bullish-run case (bearish mirrored):
  * TheSTRAT types on 1h bars (listed LTF), forex grid: 2-up = high > prev high and
    low >= prev low (equal = not taken).  A run = consecutive 2-ups; a 1, 3 or 2-down
    ends it ('a 1 or a 3 interrupting the sequence resets the count').
  * Reversal trigger = the bar right after the run's last 2-up is a 2-down (direction
    flips and price starts taking the pivots back out).  Decide at its close, SHORT.
  * Stop = the run's high (highest high of the run bars).  Target = the low of the bar
    before the first 2-up of the run: the retrace back through the whole pivot stack
    ('accelerates the move back through the previous range').  max_hold 24h.
  * Baseline book = every such reversal after a run of >= 2 same-direction 2s.
    Gate machine_gun = run length >= 5 ('five or more').  Claim '+': reversals out of a
    >=5 stack reach the base better (control-adjusted) than out of a 2-4 stack.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_guest_01b")
from common01b import cl, bars_arr, strat_types, to_utc  # noqa: E402

TF = "1h"
MIN_RUN = 2
MG = 5
MAX_HOLD = "24h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bars_arr(cl.build_bars(m1, TF))
    h, l, c = b["h"], b["l"], b["c"]
    t = strat_types(h, l)
    n = len(t)
    rows = []
    run_up = run_dn = 0
    for i in range(1, n):
        # bar i is the trigger if the previous bars form a run
        if t[i] == -2 and run_up >= MIN_RUN:
            s = i - run_up                      # first 2-up bar
            if s - 1 >= 0 and t[s - 1] != 0:
                rows.append((i, -1, float(h[s:i].max()), float(l[s - 1]), run_up))
        if t[i] == 2 and run_dn >= MIN_RUN:
            s = i - run_dn
            if s - 1 >= 0 and t[s - 1] != 0:
                rows.append((i, 1, float(l[s:i].min()), float(h[s - 1]), run_dn))
        run_up = run_up + 1 if t[i] == 2 else 0
        run_dn = run_dn + 1 if t[i] == -2 else 0
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "run_len", "machine_gun"]
    if not rows:
        return pd.DataFrame(columns=cols)
    f = pd.DataFrame(rows, columns=["bar", "direction", "stop_px", "target_px", "run_len"])
    cl_ = c[f["bar"].to_numpy()]
    d = f["direction"].to_numpy()
    ok = (d * (f["target_px"].to_numpy() - cl_) > 0) & (d * (cl_ - f["stop_px"].to_numpy()) > 0)
    f = f[ok].copy()
    f["decision_time"] = to_utc(b["close_t"][f["bar"].to_numpy()])
    f["available_at"] = f["decision_time"]
    f["machine_gun"] = f["run_len"].to_numpy() >= MG
    return f[cols].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"pmg_{TF}_{MIN_RUN}_{MG}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.machine_gun.mean(), ev.run_len.value_counts().sort_index().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "machine_gun", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "ctrl_overlap", "exposure_bars", "control"):
        print(k, res.get(k))
    op = {"rules": [
        "1h bars (forex grid); STRAT types vs previous bar, equal extremes not taken.",
        "Run = consecutive same-direction 2s; trigger = the next bar is a 2 in the opposite direction; decide at its close against the run.",
        "Stop = run extreme; target = the opposite extreme of the bar before the run's first 2 (retrace through the whole stack); max_hold 24h.",
        "Book = runs >= 2; gate machine_gun = run >= 5; complement = runs of 2-4."],
        "params": {"tf": TF, "min_run_baseline": MIN_RUN, "machine_gun_len": MG, "max_hold": MAX_HOLD,
                   "grid4h": "forex (n/a at 1h)"}}
    ps = {"tf": "declared-before-run: 1h (listed LTF)",
          "min_run_baseline": "declared-before-run: shortest multi-pivot stack (2) as the 'shorter one' of the measurable",
          "machine_gun_len": "corpus: 1XWyy6Q-_8Q 'twos to the upside all in the same direction for five or more candles'",
          "max_hold": "declared-before-run: 24h",
          "grid4h": "declared-before-run: forex grid default"}
    notes = "Speed/acceleration is scored as reaching the stack's base before the run extreme, control-adjusted."
    print(cl.write_result("pivot-machine-gun", None, res, operationalization=op, params_source=ps,
                          script=__file__, probe=probe, notes=notes))
