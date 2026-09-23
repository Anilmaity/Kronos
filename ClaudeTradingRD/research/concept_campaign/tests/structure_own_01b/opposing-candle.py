"""opposing-candle — opposing candles as a series (specified).

Concept: concepts/structure/opposing-candle.yaml (sunday_sessions_live_q_a_03).

Reading a — the qualification rule (gate_test, claim '+'):
  "not every opposing-coloured candle qualifies: a candle that simply opens and delivers in
  one direction with no wick does not make a relevant high or low and gives no validation."
  Baseline = every phase-3 rung-0 15m CISD (the series is "the raw material for ... his
  CISD"): series_open, 2/2, max_wait 3, protected-swing stop, 2R, 150 min. Gate = every
  candle of the opposing series has OHLC shape on the extreme side (down-close candles into
  a low each have close > low; up-close candles into a high each have high > close) — i.e.
  the series is made of qualifying opposing candles, not wickless ones.

Reading b — the rolling invalidation (trade_test):
  "While expansion continues, each newly formed opposing candle supplies the current
  invalidation level: its extreme should not be traded back to." On 1h bars, inside a live
  expansion (latest 1h expansion event, threshold_fits §2, decided before the candle, at
  most 24 bars old, its origin not yet traded through), at the close of each new opposing
  candle that qualifies (down-close with a lower wick in a bull leg; mirror) enter WITH the
  trend ("support from the series when trading with the trend"), stop beyond the extreme of
  the contiguous opposing series ending at that candle, target = the leg's extreme since
  the expansion broke ("next relevant level"), 10h trading-time hold, clustered by leg.
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

CID = "opposing-candle"
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "rr", "wicked"]


def detect_a(m1):
    b, ev = C.cisd15(m1)
    if ev.empty:
        return C.empty_frame(COLS_A[:-1], extra_bool=("wicked",))
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ok = np.zeros(len(ev), bool)
    for k, (s, e, d) in enumerate(zip(ev["s_pos"].to_numpy(), ev["e_pos"].to_numpy(),
                                      ev["d"].to_numpy())):
        r = slice(int(s), int(e) + 1)
        ok[k] = bool(((c[r] - l[r]) > 0).all()) if d == 1 else bool(((h[r] - c[r]) > 0).all())
    t = pd.DatetimeIndex(ev["close_time"])
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": ev["d"].to_numpy(),
                         "stop_px": ev["protected_swing"].to_numpy(dtype=float), "rr": 2.0,
                         "wicked": ok})


MAX_AGE = 24
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "target_px", "e_id"]


def detect_b(m1):
    b = cl.build_bars(m1, "1h")
    ex = C.expansions(b)
    if ex.empty:
        return C.empty_frame(COLS_B)
    o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
    ct = b["close_time"].to_numpy()
    E_dir = ex["dir"].to_numpy()
    E_brk = ex["break_pos"].to_numpy()
    E_dec = ex["dec_pos"].to_numpy()
    E_org = ex["origin"].to_numpy()
    # latest expansion decided by each bar's close, by position (dec_pos <= i)
    order = np.argsort(E_dec, kind="stable")
    dec_sorted = E_dec[order]
    rows = []
    for i in range(len(b)):
        j = np.searchsorted(dec_sorted, i, side="right") - 1
        if j < 0:
            continue
        k = order[j]
        dp, d = int(E_dec[k]), int(E_dir[k])
        if not (dp < i <= dp + MAX_AGE):
            continue
        # a qualifying opposing candle (down-close with a lower wick in a bull leg)
        if d == 1 and not (c[i] < o[i] and c[i] > l[i]):
            continue
        if d == -1 and not (c[i] > o[i] and c[i] < h[i]):
            continue
        # origin not traded through since the expansion was decided
        if d == 1 and l[dp + 1:i + 1].min() <= E_org[k]:
            continue
        if d == -1 and h[dp + 1:i + 1].max() >= E_org[k]:
            continue
        # contiguous opposing series ending at i
        s = i
        while s - 1 > dp and ((c[s - 1] < o[s - 1]) if d == 1 else (c[s - 1] > o[s - 1])):
            s -= 1
        stop = l[s:i + 1].min() if d == 1 else h[s:i + 1].max()
        seg = slice(int(E_brk[k]), i + 1)
        tgt = h[seg].max() if d == 1 else l[seg].min()
        rows.append({"decision_time": ct[i], "available_at": ct[i], "direction": d,
                     "stop_px": float(stop), "target_px": float(tgt),
                     "e_id": float(b.index[int(E_brk[k])].value)})
    if not rows:
        return C.empty_frame(COLS_B)
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = pd.DatetimeIndex(out["available_at"])
    return out[COLS_B]


EXP_SRC = ("threshold_fits: §2 displacement=aggressive, close-beyond gate (grade A) + N=4 "
           "window r>=1.5, d>=0.65 vs the pre-break 4-bar range (grade B); 2/2 fractal swings")


def run_a():
    ev = cl.cache_frame("so01b_oc_a_cisd15_wick", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev), "wicked", int(ev["wicked"].sum()))
    probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
    res = cl.gate_test(ev, "wicked", mask_available_at="decision_time", max_hold="150min")
    C.show(res)
    op = {"rules": [
        "baseline: phase-3 rung-0 15m CISD (series_open, 2/2 swing, max_wait 3, min_series "
        "1); decide at the confirming close; next M1 open; stop at protected swing; 2R; 150 min",
        "gate wicked: every candle of the opposing series has a wick on the extreme side "
        "(bullish case: each down-close candle close > low; bearish: each up-close candle "
        "high > close); claim '+'"],
        "params": {"tf": "15min", "min_wick": 0.0, "rr": 2.0, "max_hold": "150min"}}
    src = {"tf": "phase3: primary 15m CISD rung-0 book (§1.8)",
           "min_wick": "corpus: opposing-candle ambiguity 'No minimum wick size is given' -> "
                       "any wick > 0",
           "rr": "phase3: §1.12 2R", "max_hold": "phase3: §1.13 10 entry-TF bars",
           "gate": "corpus: opposing-candle 'a candle that opens and goes straight lower with "
                   "no wick is not counted as an opposing candle'"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe)
    print("wrote", p)


def run_b():
    ev = cl.cache_frame("so01b_oc_b_1h_roll", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev))
    probe = cl.probe_lookahead(detect_b, ev, lookback="30D")
    res = cl.trade_test(ev, max_hold="10h", hold_basis="bars", ctrl_tod_tol_min=30,
                        cluster="e_id")
    C.show(res)
    op = {"rules": [
        "1h UTC bars; live expansion = latest 1h expansion event (close beyond 2/2 swing, "
        "4-bar window range/pre-range >= 1.5, distance/pre-range >= 0.65) decided 1..24 bars "
        "before, its origin not traded through since",
        "at the close of each qualifying opposing candle (bull leg: down-close with close > "
        "low; mirror) enter with the trend at the next M1 open",
        "stop = extreme of the contiguous opposing series ending at that candle; target = "
        "the leg's extreme since the expansion's break; 10h trading time; NY clock +/-30 "
        "min control; clustered by expansion leg"],
        "params": {"tf": "1h", "exp_n": 4, "exp_r": 1.5, "exp_d": 0.65, "max_age": MAX_AGE,
                   "max_hold": "10h", "hold_basis": "bars", "ctrl_tod_tol_min": 30,
                   "cluster": "expansion leg"}}
    src = {"tf": "declared-before-run: 1h (concept ltf list 1H)",
           "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
           "max_age": "declared-before-run: a leg counts as live for 24 bars after it prints",
           "stop": "corpus: opposing-candle execution.stop 'Beyond the opposing candle extreme'",
           "target": "corpus: opposing-candle execution.targets 'next relevant level' -> the "
                     "leg's own extreme",
           "max_hold": "phase3: §1.13 10 entry-TF bars",
           "hold_basis": "declared-before-run: trading time (trap 7)",
           "ctrl_tod_tol_min": "declared-before-run: trap 9, not a timing concept",
           "cluster": "declared-before-run: one cluster per expansion leg (widens CI only)"}
    p = cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe)
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run_a()
    if "b" in which:
        run_b()
