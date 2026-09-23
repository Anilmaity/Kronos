"""loss-and-gain-limit-rules (guest: STRATalorian) - gate_test.

Concept: written daily loss, weekly loss and N-consecutive-loss limits, AND the same
limits on the winning side (euphoria is worse than fear); on hitting one, step away for
the day (or week). The guest deliberately gives no numbers, so they are DECLARED here
before the first run, mirrored loss/gain as the concept requires:

  daily   : stop for the rest of the trading day once realised R today <= -2R
            or >= +4R (two 2R winners)
  streak  : stop for the rest of the day after 3 consecutive losses or 3 consecutive
            wins (streak counters reset at each step-away)
  weekly  : stop for the rest of the trading week once realised R this week <= -5R
            or >= +10R

Tallies count only trades actually taken under the rules (gated-in), gross R from M1.
Gate `allowed` = no limit is active at the decision. claim '+': allowed trades beat
(control-adjusted) the trades taken after a limit fired - which is the concept's own
measurable "P&L of sessions continued past the Nth loss vs sessions stopped at it".
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl   # noqa: E402
import _book as bk         # noqa: E402

CID = "loss-and-gain-limit-rules"
DAY_LOSS, DAY_GAIN = -2.0, 4.0
STREAK = 3
WEEK_LOSS, WEEK_GAIN = -5.0, 10.0
TOD_TOL = 30


def detect(m1):
    ev = bk.chain(m1)
    n = len(ev)
    allowed = np.zeros(n, bool)
    R = ev["_R"].to_numpy()
    tdv = ev["tday"].to_numpy(); wkv = ev["wkey"].to_numpy()
    cur_d = cur_w = None
    R_d = R_w = 0.0
    s_l = s_w = 0
    stop_day = stop_week = False
    for k in range(n):
        if tdv[k] != cur_d:
            cur_d = tdv[k]; R_d = 0.0; stop_day = False
        if wkv[k] != cur_w:
            cur_w = wkv[k]; R_w = 0.0; stop_week = False
        ok = not (stop_day or stop_week)
        allowed[k] = ok
        if not ok or not np.isfinite(R[k]):
            continue
        r = R[k]
        R_d += r; R_w += r
        if r > 0:
            s_w += 1; s_l = 0
        elif r < 0:
            s_l += 1; s_w = 0
        if R_d <= DAY_LOSS or R_d >= DAY_GAIN or s_l >= STREAK or s_w >= STREAK:
            stop_day = True; s_l = s_w = 0
        if R_w <= WEEK_LOSS or R_w >= WEEK_GAIN:
            stop_week = True; s_l = s_w = 0
    ev["allowed"] = allowed
    return bk.public(ev, ["allowed"])


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_d{DAY_LOSS}_{DAY_GAIN}_s{STREAK}_w{WEEK_LOSS}_{WEEK_GAIN}",
                        lambda: detect(cl.load_m1()), version=bk.VERSION)
    print(len(ev), ev["allowed"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, "allowed", mask_available_at="decision_time",
                       max_hold="150min", ctrl_tod_tol_min=TOD_TOL, claim="+")
    for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": bk.BASE_RULES + [
        f"daily limits: step away for the rest of the trading day once realised R today "
        f"<= {DAY_LOSS} or >= +{DAY_GAIN}",
        f"streak limits: step away for the rest of the day after {STREAK} consecutive "
        f"losses or {STREAK} consecutive wins (counters reset at each step-away)",
        f"weekly limits: step away for the rest of the trading week once realised R this "
        f"week <= {WEEK_LOSS} or >= +{WEEK_GAIN}",
        "tallies count only trades taken under the rules; gate allowed = no limit active; "
        "complement = the trades a limit-breaker would have taken"],
        "params": {**bk.BASE_PARAMS, "day_loss_R": DAY_LOSS, "day_gain_R": DAY_GAIN,
                   "streak_n": STREAK, "week_loss_R": WEEK_LOSS, "week_gain_R": WEEK_GAIN,
                   "ctrl_tod_tol_min": TOD_TOL}}
    dec = ("declared-before-run: the guest supplies no numbers (yaml ambiguity); ")
    src = {**bk.BASE_SOURCES,
           "day_loss_R": dec + "-2R, the two-loss daily cap two other guests state "
                               "(risk-limits-and-trade-frequency)",
           "day_gain_R": dec + "+4R, mirror of the loss side = two 2R winners",
           "streak_n": dec + "3, from the concept's measurable 'trade following a "
                             "three-win streak'; mirrored to losses",
           "week_loss_R": dec + "-5R, 2.5 daily loss limits",
           "week_gain_R": dec + "+10R, mirror (2.5 daily gain limits)",
           "ctrl_tod_tol_min": "declared-before-run: not a timing rule but limit states "
                               "build up through the day (README trap 9)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Baseline = sequential 15m bare CISD book (see _book.py). "
                              "Re-run ONCE after fixing a bug in _book.py (found by the size-down-on-fear b probe): a clock-hold time exit whose hold ended inside the 17:00 NY halt freed the position slot at the last pre-halt bar instead of at the hold's wall-clock end. Second fix + re-run: same-bar opposite CISD pairs (4 of 32,827) given a deterministic order (the probe of size-down-on-fear b caught slice-dependent order). Second run before this fix: NULL, diff +0.0040 [-0.0250, +0.0338]. First (buggy-chain) run: NULL, diff +0.0015 [-0.0278, +0.0315]. "
                              "All limit values are declared (the concept gives none); "
                              "one locked run.")
    print(p)
