"""partial-profit-taking (contested) — partial at 2R + runner vs one full exit at the draw.

Reading A (TTrades' trade reviews): partial at ~2R, hold a runner to the final objective.
Reading B (interview guest): no intraday partials — exit in full at the anticipated draw.
The concept's own measurable: "expectancy of partial-at-2R-plus-runner vs single full exit
at the draw, on the same trade sequence".

Book: the phase-3 1h CISD entries whose draw on liquidity — the previous trading day's
high (long) / low (short), spec §1.2 rule 1 + §5.2 item 1 — sits at least 2R from the
protected-swing stop (Reading A's precondition: an intermediate level at ~2R between
entry and the final target). Each entry is scored as:
  * position A = two equal legs (rows): leg 1 exits at 2R, leg 2 (runner) at the draw;
    same stop, no trail (the harness has no stop modification — the trailed runner of
    Reading A is not modelled; the concept notes that in both reviews the trail added
    nothing over the take-profit level).
  * position B = one row exiting in full at the draw.
Arm means = mean position R (equal-size legs). Hold 10h (phase-3).
  reading a: mask = A rows, claim '+' (partials are better)
  reading b: mask = B rows, claim '+' (a single exit at the draw is better)
The two readings are the same comparison with opposite claims (mirror images).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_raw, utc_ns, PHASE3_SRC  # noqa: E402

CID = "partial-profit-taking"
HOLD = "10h"
PARTIAL_R = 2.0


def detect(m1):
    b, ev = cisd_raw(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px",
            "partial", "full_exit"]
    if ev is None:
        return pd.DataFrame(columns=cols)
    ph = cl.prior_hilo(ev["decision_time"], "1D", m1=m1, min_coverage=0.5)
    s = ev["direction"].to_numpy()
    close, stop = ev["close_px"].to_numpy(), ev["stop_px"].to_numpy()
    draw = np.where(s > 0, ph["high"].to_numpy(float), ph["low"].to_numpy(float))
    risk = s * (close - stop)
    room = s * (draw - close)
    ok = np.isfinite(draw) & (risk > 0) & (room >= PARTIAL_R * risk)
    av = pd.to_datetime(np.maximum(utc_ns(pd.DatetimeIndex(ev["available_at"])[ok]),
                                   utc_ns(pd.DatetimeIndex(ph["available_at"])[ok])), utc=True)
    base = pd.DataFrame({"decision_time": pd.DatetimeIndex(ev["decision_time"])[ok],
                         "available_at": av, "direction": s[ok], "stop_px": stop[ok]})
    leg1 = base.assign(target_px=close[ok] + s[ok] * PARTIAL_R * risk[ok], partial=True,
                       full_exit=False, _o=0)
    leg2 = base.assign(target_px=draw[ok], partial=True, full_exit=False, _o=1)
    full = base.assign(target_px=draw[ok], partial=False, full_exit=True, _o=2)
    return pd.concat([leg1, leg2, full]).sort_values(["decision_time", "_o"], kind="stable") \
        .reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("ppt_cisd1h_pdh_2r_partial_vs_full", lambda: detect(cl.load_m1()))
    print("rows", len(ev), "entries", int(ev["full_exit"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    op_rules = [
        "entries: 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming "
        "bar close, enter next M1 open, stop at the protected swing, exit by 10h",
        "universe: previous trading day's high (long) / low (short) >= 2R from the stop, "
        "measured from the decision close (prior_hilo 1D, min_coverage 0.5)",
        "position A: two equal legs, leg 1 target = decision close + 2R, leg 2 target = the "
        "draw; position B: one leg, target = the draw; no trailing / no break-even"]
    params = {"tf": "1h", "partial_at_R": PARTIAL_R, "partial_fraction": 0.5,
              "draw": "PDH/PDL", "min_coverage": 0.5, "max_hold": HOLD}
    src = {"tf": PHASE3_SRC, "max_hold": PHASE3_SRC,
           "partial_at_R": "method_spec §5.5: 'partial at ~2R' (Reading A)",
           "partial_fraction": "declared-before-run: fraction never given in Reading A "
                               "('no position fractions are ever given'); equal legs",
           "draw": "method_spec §1.2 rule 1 + §5.2 item 1: previous candle's extreme on "
                   "the paired HTF",
           "min_coverage": "declared-before-run: skip stub sessions (README trap 6)"}
    for reading, mask in (("a", "partial"), ("b", "full_exit")):
        res = cl.gate_test(ev, mask, mask_available_at="decision_time", max_hold=HOLD,
                           claim="+")
        print(reading, {k: res.get(k) for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi",
                                                "p", "mde", "verdict", "verdict_detail",
                                                "ties", "ctrl_overlap")})
        op = {"rules": op_rules + [f"gated = {'position A (partial + runner)' if mask == 'partial' else 'position B (full exit at the draw)'}; claim '+'"],
              "params": params}
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe,
                            notes="Readings a and b are the same stacked comparison with "
                                  "opposite claims. The runner's trailed stop (Reading A) "
                                  "cannot be expressed in the harness (fixed stop only); "
                                  "the runner holds the original stop to the draw or 10h.")
        print("wrote", p)
