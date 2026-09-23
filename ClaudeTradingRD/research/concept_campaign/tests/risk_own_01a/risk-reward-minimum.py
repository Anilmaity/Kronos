"""risk-reward-minimum (contested) — two readings, both on the phase-3 1h CISD book.

(a) FLOOR: "Reject a setup whose structural target is less than 2R from the stop."
    Baseline book = 1h CISD, stop at the protected swing, target = the draw on
    liquidity on the paired HTF (1H/1D pair, spec §1.2 rule 1 + §5.2 item 1: the
    previous day's high for longs / low for shorts). Gate = the draw sits >= 2R from
    the stop, measured from the decision close (known at the decision). claim '+':
    setups that clear the 2R floor are better (control-adjusted) than those that do not.
(b) 2R vs 1:1: "he declines a fixed 1:1 ... a 1:1 system needs > 50%" — the same entry
    list scored at a fixed 2R target (gated rows) and at a fixed 1R target (complement).
    claim '+': the 2R target is the better exit for these entries.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_raw, utc_ns, PHASE3_SRC  # noqa: E402

CID = "risk-reward-minimum"
HOLD = "10h"


def detect_a(m1):
    b, ev = cisd_raw(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "r_ge_2"]
    if ev is None:
        return pd.DataFrame(columns=cols)
    ph = cl.prior_hilo(ev["decision_time"], "1D", m1=m1, min_coverage=0.5)
    draw = np.where(ev["direction"] > 0, ph["high"].to_numpy(float), ph["low"].to_numpy(float))
    s = ev["direction"].to_numpy()
    risk = s * (ev["close_px"].to_numpy() - ev["stop_px"].to_numpy())
    room = s * (draw - ev["close_px"].to_numpy())
    ok = np.isfinite(draw) & (risk > 0) & (room > 0)      # draw already taken -> no target
    av = pd.DatetimeIndex(ev["available_at"])
    pav = pd.DatetimeIndex(ph["available_at"])
    out = pd.DataFrame({
        "decision_time": ev["decision_time"], "available_at": av,
        "direction": s, "stop_px": ev["stop_px"], "target_px": draw,
        "r_ge_2": (room / np.where(risk > 0, risk, np.nan)) >= 2.0})
    # latest input: the confirming bar or the prior day's close (always earlier)
    out["available_at"] = pd.to_datetime(np.maximum(utc_ns(av), utc_ns(pav)), utc=True)
    return out[ok].reset_index(drop=True)[cols]


def detect_b(m1):
    b, ev = cisd_raw(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "is_2r"]
    if ev is None:
        return pd.DataFrame(columns=cols)
    base = ev[["decision_time", "available_at", "direction", "stop_px"]]
    two = base.assign(rr=2.0, is_2r=True)
    one = base.assign(rr=1.0, is_2r=False)
    return pd.concat([two, one]).sort_values(["decision_time", "rr"], kind="stable") \
        .reset_index(drop=True)[cols]


def show(tag, r):
    keys = ("n", "n_gated", "n_complement", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde",
            "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap")
    print(tag, {k: r.get(k) for k in keys if k in r})


if __name__ == "__main__":
    # ── reading a ──
    ev = cl.cache_frame("rrmin_a_cisd1h_pdhpdl_floor2", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev), "gate rate", ev["r_ge_2"].mean())
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    res = cl.gate_test(ev, "r_ge_2", mask_available_at="decision_time", max_hold=HOLD,
                       claim="+")
    show("a", res)
    op = {"rules": [
        "baseline: 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming "
        "bar close, enter next M1 open, stop at the protected swing",
        "target = previous trading day's high (long) / low (short), prior_hilo 1D with "
        "min_coverage 0.5 (stub days skipped); events whose draw is already taken at the "
        "decision close are dropped (no structural target)",
        "gate r_ge_2: (draw - decision close) / (decision close - stop) >= 2",
        "exit at stop, target or 10h"],
        "params": {"tf": "1h", "rr_floor": 2.0, "draw": "PDH/PDL", "min_coverage": 0.5,
                   "max_hold": HOLD, "day_open_hour": 18}}
    src = {"tf": PHASE3_SRC, "max_hold": PHASE3_SRC,
           "rr_floor": "method_spec §5.3: 2R floor (three videos)",
           "draw": "method_spec §1.2 rule 1 + §5.2 item 1: targets from the paired HTF "
                   "(1H/1D), previous candle's extreme first",
           "min_coverage": "declared-before-run: skip stub sessions (README trap 6)",
           "day_open_hour": "session_window_fit: settled 18:00 NY roll"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Reading a = 2R as a FLOOR on the structural target. The "
                              "remedies (refine entry, body stop, retest) are not applied: "
                              "the gate asks only whether floor-passing setups are better.")
    print("wrote", p)

    # ── reading b ──
    evb = cl.cache_frame("rrmin_b_cisd1h_2r_vs_1r", lambda: detect_b(cl.load_m1()))
    print("b rows", len(evb))
    probe_b = cl.probe_lookahead(detect_b, evb, lookback="20D")
    res_b = cl.gate_test(evb, "is_2r", mask_available_at="decision_time", max_hold=HOLD,
                         claim="+")
    show("b", res_b)
    op_b = {"rules": [
        "baseline entries: 1h CISD as reading a (all events, no draw requirement)",
        "each entry appears twice: target 2R (gated) and target 1R (complement), same stop",
        "exit at stop, target or 10h"],
        "params": {"tf": "1h", "rr_gated": 2.0, "rr_complement": 1.0, "max_hold": HOLD}}
    src_b = {"tf": PHASE3_SRC, "max_hold": PHASE3_SRC,
             "rr_gated": "method_spec §5.3 / concept: 2R minimum",
             "rr_complement": "corpus: concept detection rule 'reject 1:1' (the named alternative)"}
    p = cl.write_result(CID, "b", res_b, operationalization=op_b, params_source=src_b,
                        script=__file__, probe=probe_b,
                        notes="Variant comparison on identical entries (stacked rows). "
                              "The two arms share entries so the two-group CI is "
                              "conservative. Each arm is adjusted by its own geometry-"
                              "matched control, so this asks whether 2R exploits these "
                              "entries better than 1R does relative to random entries.")
    print("wrote", p)
