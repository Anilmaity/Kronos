"""expansion-signature — trading inside an expansion (contested).

Concept: concepts/structure/expansion-signature.yaml.

Reading a — the continuation entry inside an expansion (trade_test):
  "wait for price to retrace into an important level (generally a fair value gap), require
  a close over the series of down-closed candles, and only then is there an invalidation"
  (46VIOAlxmEE), with the expansion's signature "very shallow moves against the trend"
  (4Gm8p6O7Ebs). Trend leg = latest 1h expansion event (threshold_fits §2) in the trade
  direction, decided before the pullback extreme; pullback shallow: (H-L)/(H-O) <= 0.50.
  Entry = phase-3 15m CISD in the trend direction whose extreme bar reached into a same-
  direction 15m FVG (formed within the 40 bars before the extreme and not yet traded
  through). Stop = the protected swing (L); target = H, the unswept high of the leg
  ("previous candles' unswept highs"); 8h trading-time hold.

Reading b — the stand-aside rule (gate_test, claim '-'):
  "after we have 3 days of expansion, this is generally when it can set up" a new phase —
  do not seek a further continuation. Baseline = phase-3 15m CISD events aligned with the
  latest 1h expansion (continuation setups). Gate = the three previous completed trading
  days (18:00 NY roll, stub sessions < 600 M1 bars skipped) were all expansion days in the
  trade direction: closed that way with a small wick (opposing run open->extreme <= body,
  threshold_fits §1 crossover 1.0).
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
from detectors.primitives import fair_value_gaps   # noqa: E402

CID = "expansion-signature"
SHALLOW = 0.50
FVG_LOOKBACK = 40
HOLD = "8h"
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "target_px", "e_id"]


def detect_a(m1):
    b15, ev = C.cisd15(m1)
    b1 = cl.build_bars(m1, "1h")
    ex = C.expansions(b1)
    if ev.empty or ex.empty:
        return C.empty_frame(COLS_A)
    cx = C.continuation_context(b15, ev, b1, ex)
    d = ev["d"].to_numpy()
    keep = (cx["aligned"].to_numpy() & cx["exp_before_ext"].to_numpy()
            & (cx["depth"].to_numpy() <= SHALLOW)
            & ((cx["h_after"].to_numpy() - cx["H"].to_numpy()) * d <= 0))
    fv = fair_value_gaps(b15[["open", "high", "low", "close"]])
    bull = np.flatnonzero(fv["bullish_fvg"].to_numpy())
    bear = np.flatnonzero(fv["bearish_fvg"].to_numpy())
    glo, ghi = fv["gap_low"].to_numpy(), fv["gap_high"].to_numpy()
    h15, l15 = b15["high"].to_numpy(), b15["low"].to_numpy()
    ext = ev["ext_pos"].to_numpy()
    in_fvg = np.zeros(len(ev), bool)
    for k in np.flatnonzero(keep):
        e = ext[k]
        if d[k] == 1:
            cand = bull[(bull < e) & (bull >= e - FVG_LOOKBACK)]
            for g in cand[::-1]:
                # reached into it on the extreme bar, not traded through it before
                if l15[e] <= ghi[g] and (g + 1 > e - 1 or l15[g + 1:e].min() >= glo[g]):
                    in_fvg[k] = True
                    break
        else:
            cand = bear[(bear < e) & (bear >= e - FVG_LOOKBACK)]
            for g in cand[::-1]:
                if h15[e] >= glo[g] and (g + 1 > e - 1 or h15[g + 1:e].max() <= ghi[g]):
                    in_fvg[k] = True
                    break
    keep &= in_fvg
    t = pd.DatetimeIndex(ev["close_time"])
    ei = cx["e_idx"].to_numpy().astype(int)
    eid = np.where(ei >= 0, pd.DatetimeIndex(ex["dec_time"]).as_unit("ns").asi8[
        np.maximum(ei, 0)], -1).astype(float)
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": cx["L"].to_numpy(), "target_px": cx["H"].to_numpy(),
                        "e_id": eid})
    return out[keep].reset_index(drop=True)


COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr", "exp3"]


def detect_b(m1):
    b15, ev = C.cisd15(m1)
    b1 = cl.build_bars(m1, "1h")
    ex = C.expansions(b1)
    if ev.empty or ex.empty:
        return C.empty_frame(COLS_B[:-1], extra_bool=("exp3",))
    t = pd.DatetimeIndex(ev["close_time"])
    ei = C.latest_idx(pd.DatetimeIndex(ex["dec_time"]), t)
    d = ev["d"].to_numpy()
    aligned = (ei >= 0) & (ex["dir"].to_numpy()[np.maximum(ei, 0)] == d)
    day = cl.build_bars(m1, "1D")
    day = day[day["n_m1"] >= 600]
    o, h, l, c = (day[x].to_numpy() for x in ("open", "high", "low", "close"))
    body = np.abs(c - o)
    run_up = o - l          # opposing run of a bullish day (open -> low)
    run_dn = h - o          # opposing run of a bearish day (open -> high)
    exp_bull = (c > o) & (run_up <= body)
    exp_bear = (c < o) & (run_dn <= body)
    dct = pd.DatetimeIndex(day["close_time"]).as_unit("ns").asi8
    j = np.searchsorted(dct, t.as_unit("ns").asi8, side="right") - 1   # last completed day
    exp3 = np.zeros(len(ev), bool)
    okj = j >= 2
    jj = np.maximum(j, 2)
    for sgn, arr in ((1, exp_bull), (-1, exp_bear)):
        s = okj & (d == sgn)
        exp3[s] = arr[jj[s]] & arr[jj[s] - 1] & arr[jj[s] - 2]
    keep = aligned
    return pd.DataFrame({"decision_time": t[keep], "available_at": t[keep],
                         "direction": d[keep],
                         "stop_px": ev["protected_swing"].to_numpy(dtype=float)[keep],
                         "rr": 2.0, "exp3": exp3[keep].astype(bool)}).reset_index(drop=True)


EXP_SRC = ("threshold_fits: §2 displacement=aggressive, close-beyond gate (grade A) + N=4 "
           "window r>=1.5, d>=0.65 vs the pre-break 4-bar range (grade B); 2/2 fractal swings")


def run_a():
    ev = cl.cache_frame("so01b_expsig_a", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="45D")
    res = cl.trade_test(ev, max_hold=HOLD, hold_basis="bars", ctrl_tod_tol_min=30,
                        cluster="e_id")
    C.show(res)
    op = {"rules": [
        "trend leg = latest 1h expansion event (close beyond 2/2 swing; 4-bar window "
        "range/pre-range >= 1.5, distance/pre-range >= 0.65) in the trade direction, decided "
        "before the pullback extreme; O = extreme behind its move; H = furthest 15m extreme "
        "from its break bar to the pullback extreme L",
        "shallow: (H-L)/(H-O) <= 0.50; H not traded through before the CISD close",
        "entry trigger: phase-3 15m CISD in the trend direction whose extreme bar reached "
        "into a same-direction 15m FVG formed within the prior 40 bars and not traded "
        "through before the extreme bar (important level = FVG)",
        "enter next M1 open; stop L (new protected swing); target H; 8h trading time; "
        "control holds NY clock +/-30 min"],
        "params": {"trend_tf": "1h", "entry_tf": "15min", "exp_n": 4, "exp_r": 1.5,
                   "exp_d": 0.65, "shallow": SHALLOW, "fvg_lookback": FVG_LOOKBACK,
                   "cisd": "series_open/2-2/mw3", "max_hold": HOLD, "hold_basis": "bars",
                   "ctrl_tod_tol_min": 30, "cluster": "expansion leg"}}
    src = {"trend_tf": "declared-before-run: 1h (concept ltf list 1H) carries the leg",
           "entry_tf": "method_spec: §1.3 15m CISD entry TF",
           "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
           "shallow": "threshold_fits: §3 leg-level 'shallow' default 0.50 (grade B)",
           "fvg_lookback": "phase3: poi_gate range lookback 40 bars",
           "cisd": "phase3: §1.8 series_open, 2/2, max_wait 3",
           "target": "corpus: expansion-signature execution.targets 'previous candles' "
                     "unswept highs/lows' -> the leg's unswept extreme H",
           "max_hold": "declared-before-run: 8h trading time (32 entry-TF bars)",
           "hold_basis": "declared-before-run: trading time (trap 7)",
           "ctrl_tod_tol_min": "declared-before-run: trap 9, not a timing concept",
           "cluster": "declared-before-run: one cluster per expansion leg (widens CI only)"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Overlaps retracement-phase's continuation book; this reading "
                              "adds the FVG 'important level' and drops the slow/quick split.")
    print("wrote", p)


def run_b():
    ev = cl.cache_frame("so01b_expsig_b", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev), "exp3", int(ev["exp3"].sum()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="30D")
    res = cl.gate_test(ev, "exp3", mask_available_at="decision_time", max_hold="150min",
                       claim="-")
    C.show(res)
    op = {"rules": [
        "baseline: phase-3 rung-0 15m CISD (series_open, 2/2, max_wait 3; protected-swing "
        "stop; 2R; 150 min) kept when aligned with the latest 1h expansion event",
        "expansion day = trading day (18:00 NY roll, >= 600 M1 bars) closing in the trade "
        "direction with opposing run (open->low for up days) <= body",
        "gate exp3: the three most recent completed (non-stub) trading days are all expansion "
        "days in the trade direction; claim '-' (stand aside after 3 days of expansion)"],
        "params": {"baseline_tf": "15min", "phase_tf": "1h", "exp_n": 4, "exp_r": 1.5,
                   "exp_d": 0.65, "n_days": 3, "small_wick_cut": 1.0, "min_day_m1": 600,
                   "rr": 2.0, "max_hold": "150min"}}
    src = {"baseline_tf": "phase3: primary 15m CISD rung-0 book (§1.8)",
           "phase_tf": "declared-before-run: 1h above the 15m entry",
           "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
           "n_days": "corpus: 4Gm8p6O7Ebs 'after we have 3 days of expansion, this is "
                     "generally when it can set up'",
           "small_wick_cut": "threshold_fits: §1 small wick = opposing_run/body <= 1.0 (grade A)",
           "min_day_m1": "declared-before-run: trap 6 stub sessions skipped",
           "rr": "phase3: §1.12 2R", "max_hold": "phase3: §1.13 10 entry-TF bars"}
    p = cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe)
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run_a()
    if "b" in which:
        run_b()
