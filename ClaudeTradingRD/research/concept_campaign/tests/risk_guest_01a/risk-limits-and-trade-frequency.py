"""risk-limits-and-trade-frequency (guests: $niper, Trader T; variant: Ash) - contested.

Two distinct readings, each a gate_test on the sequential baseline book:

 (a) two-loss daily stop ($niper, Trader T): after the 2nd losing trade of the trading
     day (the -2R daily floor at 1R per loss), stop for the day. Gate `before_2nd_loss`
     = fewer than 2 losses taken earlier today. claim '+': trades before the stop beat
     the trades a trader would take after two losses ("reading the market wrong today").
 (b) hard frequency caps (variant definition): at most one trade per day and two per
     week, regardless of outcome. Gate `in_freq_cap` = the day's first taken trade, and
     fewer than two trades taken so far this trading week. claim '+'.

Risk "<1% per trade" and "1-2R" are sizing / payoff arithmetic, R-invariant: the book
already uses 2R ("the model's target is 2R").
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl   # noqa: E402
import _book as bk         # noqa: E402

CID = "risk-limits-and-trade-frequency"
MAX_LOSSES = 2
PER_DAY, PER_WEEK = 1, 2
TOD_TOL = 30


def detect_a(m1):
    ev = bk.chain(m1)
    ev["before_2nd_loss"] = ev["day_losses_before"] < MAX_LOSSES
    return bk.public(ev, ["day_losses_before", "before_2nd_loss"])


def detect_b(m1):
    ev = bk.chain(m1)
    n = len(ev)
    ok = np.zeros(n, bool)
    tdv = ev["tday"].to_numpy(); wkv = ev["wkey"].to_numpy()
    cur_d = cur_w = None
    nd = nw = 0
    for k in range(n):
        if tdv[k] != cur_d:
            cur_d = tdv[k]; nd = 0
        if wkv[k] != cur_w:
            cur_w = wkv[k]; nw = 0
        if nd < PER_DAY and nw < PER_WEEK:
            ok[k] = True
            nd += 1; nw += 1
        else:
            nd = max(nd, PER_DAY)   # the day is over once its one trade is taken
    ev["in_freq_cap"] = ok
    return bk.public(ev, ["in_freq_cap"])


def run(reading, detect, col, rules, params, srcs):
    ev = cl.cache_frame(f"{CID}_{reading}_{MAX_LOSSES}_{PER_DAY}_{PER_WEEK}",
                        lambda: detect(cl.load_m1()), version=bk.VERSION)
    print(reading, len(ev), ev[col].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, col, mask_available_at="decision_time",
                       max_hold="150min", ctrl_tod_tol_min=TOD_TOL, claim="+")
    for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(" ", k, res.get(k))
    op = {"rules": bk.BASE_RULES + rules,
          "params": {**bk.BASE_PARAMS, **params, "ctrl_tod_tol_min": TOD_TOL}}
    src = {**bk.BASE_SOURCES, **srcs,
           "ctrl_tod_tol_min": "declared-before-run: not a timing rule but the gated "
                               "trades sit early in the trading day (README trap 9)"}
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Baseline = sequential 15m bare CISD book (see _book.py). "
                              "Re-run ONCE after fixing a bug in _book.py (found by the size-down-on-fear b probe): a clock-hold time exit whose hold ended inside the 17:00 NY halt freed the position slot at the last pre-halt bar instead of at the hold's wall-clock end. Second fix + re-run: same-bar opposite CISD pairs (4 of 32,827) given a deterministic order (the probe of size-down-on-fear b caught slice-dependent order). Second run before this fix: a NULL diff +0.0124 [-0.0184, +0.0423]; b UNDERPOWERED diff +0.0376 [-0.0368, +0.1132]. First (buggy-chain) run: a NULL diff -0.0038 [-0.0338, +0.0257]; b UNDERPOWERED diff -0.0018 [-0.0756, +0.0719]. "
                              "Break-even (R == 0) trades are not losses; every taken "
                              "trade counts toward frequency caps.")
    print(p)


if __name__ == "__main__":
    run("a", detect_a, "before_2nd_loss",
        [f"gate before_2nd_loss: fewer than {MAX_LOSSES} losing trades (gross R < 0) "
         "taken earlier in this trading day (18:00 NY roll); complement = trades after "
         "the second loss"],
        {"max_losses_per_day": MAX_LOSSES, "counter_reset": "trading day (18:00 NY)"},
        {"max_losses_per_day": "corpus: wCtxmWe4KNc 'I take two losses in a day then I "
                               "shut it down for the day'",
         "counter_reset": "corpus: UmLWRlXd_V8 'two losses in uh a session' / Trader T "
                          "'in a day'; session_window_fit: 18:00 NY roll"})
    run("b", detect_b, "in_freq_cap",
        [f"gate in_freq_cap: at most {PER_DAY} trade per trading day (the day's first "
         f"taken trade) and at most {PER_WEEK} per trading week, regardless of result; "
         "complement = every trade the caps forbid"],
        {"per_day": PER_DAY, "per_week": PER_WEEK,
         "week_reset": "Sunday 18:00 NY session"},
        {"per_day": "corpus: variant definition 'A maximum of one trade is taken per day'",
         "per_week": "corpus: variant definition 'a maximum of two per week'",
         "week_reset": "declared-before-run: yaml ambiguity (Sunday vs first trading "
                       "day) - the trading week opens at the Sunday 18:00 NY session"})
