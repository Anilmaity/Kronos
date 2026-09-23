"""daily-close-only-bias (guest: Jokerszn) -> gate_test.

Measurable (the concept's own): "continuation rate after a daily body close through a level
vs a wick-only breach". Declared before the first run:
  * Level = the previous trading day's high / low (the "old highs and lows" wicks take).
    Daily bars, 18:00 NY roll.
  * Baseline book: every day that breaches exactly ONE side of the previous day (high > PDH
    with low >= PDL, or mirrored). Trade the breach direction (continuation) at that day's
    close: decide at the daily close_time, harness enters next M1 open.
    Stop = the breach day's opposite extreme; target 1R; hold one trading day
    (23h of trading bars, hold_basis="bars").
  * Gate (claim '+'): the breach day CLOSED beyond the level (body close through PDH/PDL).
    Complement = wick-only breaches (closed back inside). The concept says only the body
    close is a directional signal, so gated continuation must beat wick-only continuation.
  * First run used ctrl_tod_tol_min=30; with every decision at the 17:00 NY close (inside the
    daily halt) and the minute-of-hour grid, 43% of trades got NO control and 38% of control
    draws were the trade's own 18:00 entry bar. That is a control-design bug in this script:
    fixed by dropping the TOD tolerance (default control), re-run once.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "daily-close-only-bias"
MAX_HOLD = "23h"
RR = 1.0
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "body_close"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    if len(d) < 3:
        return pd.DataFrame(columns=COLS)
    H, L, C = d["high"].to_numpy(float), d["low"].to_numpy(float), d["close"].to_numpy(float)
    ph, pl = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    up = (H > ph) & (L >= pl)
    dn = (L < pl) & (H <= ph)
    ct = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC")
    # an in-progress last bar has close_time beyond the data, so its event is never scored early
    sel = (up | dn).copy()
    sel[0] = False
    ev = pd.DataFrame({
        "decision_time": ct[sel], "available_at": ct[sel],
        "direction": np.where(up[sel], 1, -1),
        "stop_px": np.where(up[sel], L[sel], H[sel]),
        "rr": RR,
        "body_close": np.where(up[sel], C[sel] > ph[sel], C[sel] < pl[sel]),
    })
    ev["body_close"] = ev["body_close"].astype(bool)
    return ev.reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame("dcob_pdhl_1r", lambda: detect(cl.load_m1()))
    print(len(ev), ev["body_close"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "body_close", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       hold_basis="bars")
    for k in ("n", "n_gated", "n_complement", "firing_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "gated", "complement", "ties", "ctrl_overlap"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "daily bars (18:00 NY roll); breach day = takes exactly one side of the previous day's range",
        "baseline: trade the breach direction at the breach day's close; stop = breach day's opposite extreme; 1R; hold 1 trading day (bars)",
        "gate: breach day closed beyond the previous day's high/low (body close through the level); complement = wick-only breach",
        "claim '+': body-close continuation beats wick-only continuation, control-adjusted"],
        "params": {"level": "PDH/PDL", "rr": RR, "max_hold": MAX_HOLD, "hold_basis": "bars",
                   "stop": "breach-day opposite extreme", "grid4h": "n/a (1D)"}}
    src = {"level": "corpus: JABOO4LYNjQ 'wicks ... taking liquidity from old highs and lows' - the previous day's high/low",
           "rr": "declared-before-run: 1R symmetric continuation target (no magnitude stated)",
           "max_hold": "declared-before-run: bias is re-evaluated at every daily close -> one trading day",
           "hold_basis": "declared-before-run: one trading day of bars; daily-close entries straddle weekends",
           "stop": "declared-before-run: the breach day's opposite extreme (the day's own range)",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Re-run once after a script bug: the first run's ctrl_tod_tol_min=30 left 43% of "
                              "trades without a control (decisions sit in the 17:00 NY halt) and 38% control overlap; "
                              "first run was UNDERPOWERED, diff -0.108 [-0.219, +0.002]. This run uses the default control.")
    print(p)
