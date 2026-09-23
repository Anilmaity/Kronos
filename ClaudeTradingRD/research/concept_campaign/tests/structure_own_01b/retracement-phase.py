"""retracement-phase — the slow, shallow counter-move between two expansions (contested).

Concept: concepts/structure/retracement-phase.yaml. The contested point is the one the
concept itself names: a retracement is SLOW ("9 hours worth of candles took up the range of
about three hours", F0G31iLVpVg) versus QUICK ("you want to see them be quick", WiYZKc6ZAxA).
Both readings are traded with the concept's own execution and differ only in that clause.

Shared construction (trade_test):
  * trend leg: the latest 1h expansion event (threshold_fits §2 definition) decided at or
    before the entry decision, printed before the pullback extreme, in the trade direction;
    origin O = the extreme behind its move; leg extreme H = the furthest 15m high (bull)
    from the expansion's break bar to the pullback extreme.
  * pullback extreme L = the extreme of a phase-3 15m CISD in the trend direction
    ("wait until that retracement phase is over, drop to the lower timeframe for a change
    in the state of delivery"). Shallow: (H-L)/(H-O) <= 0.50 (threshold_fits §3 default).
  * enter at the CISD close (next M1 open); stop = L (the low that formed); target = H
    (the failure swings / previous extreme left on the opposing side); rows where H was
    already traded through between L and the CISD close are dropped; 8h trading-time hold.
Reading a (slow):  time(H -> L) >= time(O -> H)   — the retracement consumes more time.
Reading b (quick): time(H -> L) <  time(O -> H).
All parameters declared before the first run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402

CID = "retracement-phase"
SHALLOW = 0.50
HOLD = "8h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "e_id"]


def make_detect(slow: bool):
    def detect(m1):
        b15, ev = C.cisd15(m1)
        b1 = cl.build_bars(m1, "1h")
        ex = C.expansions(b1)
        if ev.empty or ex.empty:
            return C.empty_frame(COLS)
        cx = C.continuation_context(b15, ev, b1, ex)
        d = ev["d"].to_numpy()
        keep = (cx["aligned"].to_numpy() & cx["exp_before_ext"].to_numpy()
                & (cx["depth"].to_numpy() <= SHALLOW)
                & ((cx["h_after"].to_numpy() - cx["H"].to_numpy()) * d <= 0))
        is_slow = (cx["tL"].to_numpy() - cx["tH"].to_numpy()) >= \
            (cx["tH"].to_numpy() - cx["tO"].to_numpy())
        keep &= is_slow if slow else ~is_slow
        t = pd.DatetimeIndex(ev["close_time"])
        ei = cx["e_idx"].to_numpy().astype(int)
        eid = np.where(ei >= 0, pd.DatetimeIndex(ex["dec_time"]).as_unit("ns").asi8[
            np.maximum(ei, 0)], -1).astype(float)
        out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                            "stop_px": cx["L"].to_numpy(), "target_px": cx["H"].to_numpy(),
                            "e_id": eid})
        return out[keep].reset_index(drop=True)
    return detect


EXP_SRC = ("threshold_fits: §2 displacement=aggressive, close-beyond gate (grade A) + N=4 "
           "window r>=1.5, d>=0.65 vs the pre-break 4-bar range (grade B); 2/2 fractal swings")
PARAMS_SOURCE = {
    "trend_tf": "declared-before-run: 1h (concept htf list 1H) carries the expansion leg",
    "entry_tf": "method_spec: §1.3 15m CISD entry; concept ltf list 15m",
    "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
    "shallow": "threshold_fits: §3 leg-level 'shallow' default 0.50 (grade B)",
    "cisd": "phase3: §1.8 series_open, 2/2, max_wait 3, min_series 1",
    "stop": "corpus: retracement-phase execution.stop 'On the wick ... of the low/high that formed'",
    "target": "corpus: retracement-phase execution.targets 'the failure swings left on the "
              "opposing side' / 'previous candle extremes' -> the leg extreme H",
    "slow_vs_quick": "corpus: F0G31iLVpVg '9 hours worth of candles took up the range of about "
                     "three hours' (a) vs WiYZKc6ZAxA 'you want to see them be quick' (b); "
                     "cut at retracement time == leg time",
    "max_hold": "declared-before-run: 8h of trading time (32 entry-TF bars) for the H target",
    "hold_basis": "declared-before-run: trading time (trap 7)",
    "ctrl_tod_tol_min": "declared-before-run: trap 9, concept is not about timing",
    "cluster": "declared-before-run: one cluster per 1h expansion leg (widens CI only)",
}


def run(reading: str, slow: bool):
    detect = make_detect(slow)
    ev = cl.cache_frame(f"so01b_retr_{'slow' if slow else 'quick'}", lambda: detect(cl.load_m1()))
    print(reading, "events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.trade_test(ev, max_hold=HOLD, hold_basis="bars", ctrl_tod_tol_min=30,
                        cluster="e_id")
    C.show(res)
    op = {"rules": [
        "1h expansion event (close beyond 2/2 swing; 4-bar window range/pre-range >= 1.5, "
        "distance/pre-range >= 0.65) = the trend leg; origin O = extreme behind the move",
        "15m phase-3 CISD in the leg's direction whose extreme L prints after the expansion "
        "was decided; H = furthest 15m extreme from the expansion's break to L",
        "shallow: (H-L)/(H-O) <= 0.50; drop rows where H was traded through before the CISD "
        "close",
        ("slow: time(H->L) >= time(O->H)" if slow else "quick: time(H->L) < time(O->H)"),
        "enter next M1 open after the CISD close; stop L; target H; 8h trading-time hold; "
        "control holds NY clock +/-30 min"],
        "params": {"trend_tf": "1h", "entry_tf": "15min", "exp_n": 4, "exp_r": 1.5,
                   "exp_d": 0.65, "shallow": SHALLOW, "cisd": "series_open/2-2/mw3",
                   "stop": "L", "target": "H", "slow_vs_quick": "slow" if slow else "quick",
                   "max_hold": HOLD, "hold_basis": "bars", "ctrl_tod_tol_min": 30,
                   "cluster": "expansion leg"}}
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=PARAMS_SOURCE,
                        script=__file__, probe=probe,
                        notes="Readings a/b are disjoint subsets of one continuation book, "
                              "split by the concept's own slow-vs-quick contradiction.")
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run("a", True)
    if "b" in which:
        run("b", False)
