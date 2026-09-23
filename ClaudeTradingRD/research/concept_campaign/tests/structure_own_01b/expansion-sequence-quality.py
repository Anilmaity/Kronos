"""expansion-sequence-quality — expansion met with expansion (contested).

Concept: concepts/structure/expansion-sequence-quality.yaml.

Reading a — the INVALIDATOR / reversal prediction (rate_test):
  "if we have expansion met with expansion, then this low gets taken out" (Uzl3zYzr90Y).
  On 1h bars: E1 = an expansion event, E2 = the next expansion event, opposite direction,
  break bar 1..24 bars after E1's decision. At E2's decision, predict that E1's origin (the
  extreme behind E1's move) is traded through within the next 24 1h bars of trading time
  (1,440 M1 bars). Rows where the origin is already behind E2's decision close are dropped
  (nothing left to predict). Null = the same distance beyond price in the same direction,
  same 1,440 M1-bar horizon, at 5 matched random moments within +/-30 days.

Reading b — the DEGRADED-SEQUENCE filter (gate_test, claim '-'):
  "Three consecutive expansions with no interleaved retracement or consolidation flags a
  degraded sequence" — expansion met with expansion and then expansion again = the sequence
  degenerating into consolidation. Baseline = phase-3 rung-0 15m CISD events that are
  mechanically valid continuations (direction == latest 1h expansion). Gate = the last three
  1h expansion events (decided by the CISD decision) alternate direction (d, -d, d).
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

CID = "expansion-sequence-quality"
K = 24
H_BARS = 1440
COLS_A = ["decision_time", "available_at", "direction", "origin", "dec_close", "e1_id"]


def detect_a(m1):
    b = cl.build_bars(m1, "1h")
    ex = C.expansions(b)
    if len(ex) < 2:
        return C.empty_frame(COLS_A)
    c = b["close"].to_numpy()
    rows = []
    for k in range(1, len(ex)):
        e1, e2 = ex.iloc[k - 1], ex.iloc[k]
        if e1["dir"] == e2["dir"]:
            continue
        gap = int(e2["break_pos"]) - int(e1["dec_pos"])
        if not (0 < gap <= K):
            continue
        dc = c[int(e2["dec_pos"])]
        d2 = int(e2["dir"])
        if (e1["origin"] - dc) * d2 <= 0:          # origin already behind price
            continue
        rows.append({"decision_time": e2["dec_time"], "available_at": e2["dec_time"],
                     "direction": d2, "origin": float(e1["origin"]), "dec_close": float(dc),
                     "e1_id": float(b.index[int(e1["break_pos"])].value)})
    if not rows:
        return C.empty_frame(COLS_A)
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = pd.DatetimeIndex(out["available_at"])
    return out[COLS_A]


COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr", "alt3"]


def detect_b(m1):
    b15, ev = C.cisd15(m1)
    b1 = cl.build_bars(m1, "1h")
    ex = C.expansions(b1)
    if ev.empty or len(ex) < 3:
        return C.empty_frame(COLS_B[:-1], extra_bool=("alt3",))
    t = pd.DatetimeIndex(ev["close_time"])
    ei = C.latest_idx(pd.DatetimeIndex(ex["dec_time"]), t)
    d = ev["d"].to_numpy()
    ed = ex["dir"].to_numpy()
    ok = ei >= 0
    aligned = ok & (ed[np.maximum(ei, 0)] == d)
    alt = np.zeros(len(ev), bool)
    j = ei
    m = ok & (j >= 2)
    jj = np.maximum(j, 2)
    alt[m] = (ed[jj[m]] == -ed[jj[m] - 1]) & (ed[jj[m] - 1] == -ed[jj[m] - 2])
    keep = aligned
    return pd.DataFrame({"decision_time": t[keep], "available_at": t[keep],
                         "direction": d[keep],
                         "stop_px": ev["protected_swing"].to_numpy(dtype=float)[keep],
                         "rr": 2.0, "alt3": alt[keep].astype(bool)}).reset_index(drop=True)


EXP_SRC = ("threshold_fits: §2 displacement=aggressive, close-beyond gate (grade A) + N=4 "
           "window r>=1.5, d>=0.65 vs the pre-break 4-bar range (grade B); 2/2 fractal swings")


def run_a():
    pr = cl.cache_frame("so01b_esq_a_1h_k24", lambda: detect_a(cl.load_m1()))
    print("a events", len(pr))
    probe = cl.probe_lookahead(detect_a, pr, lookback="30D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(pr["decision_time"])
    d = pr["direction"].to_numpy()
    org = pr["origin"].to_numpy()
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = (org - px) * d                         # >0 when the origin is still ahead
    obs = np.full(len(t), np.nan)
    for sgn, side in ((1, "above"), (-1, "below")):
        s = d == sgn
        if s.any():
            obs[s] = cl.touch(t[s], org[s], side, horizon_bars=H_BARS)["hit"].to_numpy()
    obs[~(dist > 0)] = np.nan                     # already through at entry: dropped
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(t), np.nan)
        okk = ~tk.isna()
        pk = mkt.o[np.minimum(mkt.pos_at_or_after(tk[okk]), len(mkt.o) - 1)]
        lv = pk + d[okk] * dist[okk]
        res = np.full(okk.sum(), np.nan)
        for sgn, side in ((1, "above"), (-1, "below")):
            s = d[okk] == sgn
            if s.any():
                res[s] = cl.touch(tk[okk][s], lv[s], side, horizon_bars=H_BARS)["hit"].to_numpy()
        res[~(dist[okk] > 0)] = np.nan
        out[okk] = res
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(pr["available_at"]),
                       null_fn=null_fn, predictors=pr, cluster=pr["e1_id"].to_numpy(),
                       outcome_horizon="2D")
    C.show(res)
    op = {"rules": [
        "1h UTC-aligned bars; expansion event = close beyond a confirmed 2/2 swing, 4-bar "
        "window range/pre-range >= 1.5 and distance/pre-range >= 0.65, decided at the 4th "
        "window bar's close",
        "E2 = next expansion after E1, opposite direction, break 1..24 bars after E1's decision",
        "prediction at E2's decision: E1's origin (extreme behind its move) is traded "
        "through within 1,440 M1 bars; rows whose origin is already behind E2's decision "
        "close are dropped in the detector",
        "null: same signed distance from the first M1 open after the moment, same 1,440 "
        "M1-bar horizon, 5 matched random moments +/-30 days"],
        "params": {"tf": "1h", "exp_n": 4, "exp_r": 1.5, "exp_d": 0.65, "k_bars": K,
                   "horizon_m1_bars": H_BARS}}
    src = {"tf": "declared-before-run: 1h is in the concept's ltf list (reading b of "
                 "phases-of-price-transitions trades the same branch on 15m)",
           "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
           "k_bars": "declared-before-run: opposing expansion within 24 bars of E1",
           "horizon_m1_bars": "declared-before-run: 24 1h bars of trading time",
           "claim": "corpus: Uzl3zYzr90Y 'if we have expansion met with expansion, then this "
                    "low gets taken out'"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Rate test with a geometry-matched null (same distance, same "
                              "trading-time horizon); clustered by E1.")
    print("wrote", p)


def run_b():
    ev = cl.cache_frame("so01b_esq_b_aligned_alt3", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev), "alt3", int(ev["alt3"].sum()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="30D")
    res = cl.gate_test(ev, "alt3", mask_available_at="decision_time", max_hold="150min",
                       claim="-")
    C.show(res)
    op = {"rules": [
        "baseline: phase-3 rung-0 15m CISD (series_open, 2/2, max_wait 3; protected-swing "
        "stop; 2R; 150 min) kept only when its direction equals the latest 1h expansion "
        "event's direction (a mechanically valid continuation)",
        "gate alt3: the last three 1h expansion events decided by the CISD decision "
        "alternate direction (d, -d, d): expansion met with expansion met with expansion",
        "claim '-': the degraded sequence performs worse than the complement"],
        "params": {"baseline_tf": "15min", "phase_tf": "1h", "exp_n": 4, "exp_r": 1.5,
                   "exp_d": 0.65, "n_seq": 3, "rr": 2.0, "max_hold": "150min"}}
    src = {"baseline_tf": "phase3: primary 15m CISD rung-0 book (§1.8)",
           "phase_tf": "declared-before-run: 1h is the timeframe above the 15m entry",
           "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
           "n_seq": "corpus: expansion-sequence-quality detection rule 'Three consecutive "
                    "expansions with no interleaved retracement or consolidation'",
           "rr": "phase3: §1.12 2R", "max_hold": "phase3: §1.13 10 entry-TF bars"}
    p = cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="'Met with expansion' read as an OPPOSING expansion, so three "
                              "consecutive expansions with no retracement = alternating signs.")
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run_a()
    if "b" in which:
        run_b()
