"""phases-of-price-transitions — the legal-transition flowchart (expansion is the entry point).

Concept: concepts/structure/phases-of-price-transitions.yaml (contested).

Reading a — the REVERSAL branch as a trade (trade_test):
  "expansion -> opposing expansion := reversal". On 15m bars (ltf), an expansion event E2
  whose immediately preceding expansion event E1 is in the OPPOSITE direction and whose
  break bar comes after E1 was decided and within 24 bars of it. Trade E2's direction at
  E2's decision (close of its 4th window bar), stop = E1's extreme (the high a bullish E1
  made, up to E2's decision), target = E1's origin (the extreme behind E1's move — the
  low that "gets taken out", Uzl3zYzr90Y). Hold 12h of trading time.

Reading b — the BIAS-ALIGNMENT use (gate_test):
  "Discard a framed setup whose phase reading contradicts the standing bias." Baseline =
  every phase-3 rung-0 15m CISD (series_open, 2/2, max_wait 3, protected-swing stop, 2R,
  150 min). Phase reading at the decision = direction of the most recent 1h expansion
  event decided at or before it (a continuation keeps it, an opposing expansion flips it).
  Gate = CISD direction agrees with that reading. claim '+'.
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

CID = "phases-of-price-transitions"
TF_A = "15min"
K_A = 24
HOLD_A = "12h"
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "target_px", "e1_id"]


def detect_a(m1):
    b = cl.build_bars(m1, TF_A)
    ex = C.expansions(b)
    if len(ex) < 2:
        return C.empty_frame(COLS_A)
    h, l = b["high"].to_numpy(), b["low"].to_numpy()
    rows = []
    for k in range(1, len(ex)):
        e1, e2 = ex.iloc[k - 1], ex.iloc[k]
        if e1["dir"] == e2["dir"]:
            continue
        gap = int(e2["break_pos"]) - int(e1["dec_pos"])
        if not (0 < gap <= K_A):
            continue
        seg = slice(int(e1["break_pos"]), int(e2["dec_pos"]) + 1)
        stop = h[seg].max() if e1["dir"] == 1 else l[seg].min()
        rows.append({"decision_time": e2["dec_time"], "available_at": e2["dec_time"],
                     "direction": int(e2["dir"]), "stop_px": float(stop),
                     "target_px": float(e1["origin"]),
                     "e1_id": float(b.index[int(e1["break_pos"])].value)})
    if not rows:
        return C.empty_frame(COLS_A)
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = pd.DatetimeIndex(out["available_at"])
    return out[COLS_A]


COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr", "aligned"]


def detect_b(m1):
    b15, ev = C.cisd15(m1)
    if ev.empty:
        return C.empty_frame(COLS_B[:-1], extra_bool=("aligned",))
    b1 = cl.build_bars(m1, "1h")
    ex = C.expansions(b1)
    t = pd.DatetimeIndex(ev["close_time"])
    if ex.empty:
        al = np.zeros(len(ev), bool)
    else:
        ei = C.latest_idx(pd.DatetimeIndex(ex["dec_time"]), t)
        edir = np.where(ei >= 0, ex["dir"].to_numpy()[np.maximum(ei, 0)], 0)
        al = edir == ev["d"].to_numpy()
    return pd.DataFrame({"decision_time": t, "available_at": t,
                         "direction": ev["d"].to_numpy(),
                         "stop_px": ev["protected_swing"].to_numpy(dtype=float),
                         "rr": 2.0, "aligned": al.astype(bool)})


EXP_SRC = ("threshold_fits: §2 displacement=aggressive, close-beyond gate (grade A) + N=4 "
           "window r>=1.5, d>=0.65 vs the pre-break 4-bar range (grade B); 2/2 fractal swings")


def run_a():
    ev = cl.cache_frame("so01b_ppt_a_15m_k24", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="15D")
    res = cl.trade_test(ev, max_hold=HOLD_A, hold_basis="bars", ctrl_tod_tol_min=30,
                        cluster="e1_id")
    C.show(res)
    op = {"rules": [
        "15m UTC-aligned bars; expansion event = close beyond a confirmed 2/2 swing, then the "
        "4-bar window from the break has range/pre-range >= 1.5 and distance-beyond/pre-range "
        ">= 0.65; decided at the 4th window bar's close",
        "E2 = next expansion event after E1, opposite direction, break bar 1..24 bars after "
        "E1's decision bar (expansion met with opposing expansion = reversal)",
        "enter E2's direction at next M1 open after E2's decision; stop = E1's extreme from "
        "its break to E2's decision; target = E1's origin (the extreme behind its move)",
        "exit after 12h of trading time (720 M1 bars); control holds NY clock +/-30 min"],
        "params": {"tf": TF_A, "exp_n": 4, "exp_r": 1.5, "exp_d": 0.65, "swing": "2/2",
                   "k_bars": K_A, "max_hold": HOLD_A, "hold_basis": "bars",
                   "ctrl_tod_tol_min": 30, "cluster": "E1"}}
    src = {"tf": "declared-before-run: 15m is in the concept's ltf list; 1h had only ~830 "
                 "opposing pairs (counted before any outcome was seen)",
           "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
           "swing": "phase3: §1.8 swing left=2,right=2",
           "k_bars": "declared-before-run: 'straight into an opposing expansion' — the "
                     "opposing expansion must start within 24 bars (6h) of E1 completing",
           "max_hold": "declared-before-run: 48 entry-TF bars to allow the origin target",
           "hold_basis": "declared-before-run: trading time (trap 7, halts/weekends)",
           "ctrl_tod_tol_min": "declared-before-run: trap 9, concept is not about timing",
           "cluster": "declared-before-run: one cluster per E1 (widens CI only)",
           "stop": "corpus: EupbcX1JOsE 'expansion met with expansion, which I would view as "
                   "a reversal' — invalidation beyond the reversal's extreme",
           "target": "corpus: Uzl3zYzr90Y 'if we have expansion met with expansion, then this "
                     "low gets taken out'"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Reversal branch of the flowchart traded literally; target is "
                              "the extreme behind the first expansion.")
    print("wrote", p)


def run_b():
    ev = cl.cache_frame("so01b_ppt_b_cisd15_1hexp", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev), "aligned", int(ev["aligned"].sum()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="15D")
    res = cl.gate_test(ev, "aligned", mask_available_at="decision_time", max_hold="150min")
    C.show(res)
    op = {"rules": [
        "baseline: phase-3 rung-0 15m CISD (series_open, 2/2 swing, max_wait 3); decide at "
        "the confirming close; enter next M1 open; stop at protected swing; 2R; 150 min",
        "phase reading = direction of the latest 1h expansion event (as reading a's "
        "definition, on 1h bars) decided at or before the CISD decision",
        "gate: CISD direction == phase reading (setup aligned with the phase); claim '+'"],
        "params": {"baseline_tf": "15min", "phase_tf": "1h", "exp_n": 4, "exp_r": 1.5,
                   "exp_d": 0.65, "rr": 2.0, "max_hold": "150min"}}
    src = {"baseline_tf": "phase3: primary 15m CISD rung-0 book (§1.8)",
           "phase_tf": "declared-before-run: 1h is the timeframe above the 15m entry "
                       "(concept htf/ltf list: 1H)",
           "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
           "rr": "phase3: §1.12 2R", "max_hold": "phase3: §1.13 10 entry-TF bars",
           "gate": "corpus: ny1zkoB8MNY 'If we frame a reversal off previous day high, that "
                   "then invalidates it for me'"}
    p = cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Mask = mask_available_at decision_time: the 1h expansion used "
                              "is decided at or before the CISD close.")
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run_a()
    if "b" in which:
        run_b()
