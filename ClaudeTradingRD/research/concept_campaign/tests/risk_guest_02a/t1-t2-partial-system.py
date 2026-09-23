"""t1-t2-partial-system (guest: Alex's Options) — batch risk_guest_02a.

Claim tested: after T1 is reached, the remaining position with its stop moved to
break even (the entry price) and its target at T2 (the higher-timeframe liquidity
objective) is a positive-value leg — i.e. the "risk-free runner" beats a matched
random entry with the same geometry (same direction, stop distance = distance back
to entry, target distance to T2, same hold).

Why this leg: the 20% partial at T1 is booked identically in any variant, and trades
that stop out before T1 are identical full-risk losses in any variant. The scheme's
only decision with an outcome is what the remainder does from the T1 touch with a
break-even stop and a T2 target, so that leg is the event scored here.

Base entry model: 1h bare CISD (see _base_cisd.py). T2 := the prior completed NY
trading day's high (long) / low (short), known at the CISD decision; trades whose
PDH/PDL does not lie beyond T1 have no second target and are dropped (the concept's
precondition: "at least two structural targets").
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import concept_lab as cl  # noqa: E402
from _base_cisd import base_book, first_stop_or_t1, _ns  # noqa: E402

RUNNER_HOLD = "10h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    bk = base_book(m1)
    if bk.empty:
        return pd.DataFrame(columns=cols)
    d = cl.build_bars(m1, "1D")
    dclose = _ns(d["close_time"])
    j = np.searchsorted(dclose, bk["dec_ns"].to_numpy(), side="right") - 1
    okd = j >= 0
    pdh = np.where(okd, d["high"].to_numpy(float)[np.maximum(j, 0)], np.nan)
    pdl = np.where(okd, d["low"].to_numpy(float)[np.maximum(j, 0)], np.nan)
    long = bk["dir"].to_numpy() == 1
    t2 = np.where(long, pdh, pdl)
    t1 = bk["t1"].to_numpy()
    two = okd & np.where(long, t2 > t1, t2 < t1)
    bk = bk[two].reset_index(drop=True)
    t2 = t2[two]
    hit = first_stop_or_t1(m1, bk)
    sel = (hit["kind"].to_numpy() == 1)
    if not sel.any():
        return pd.DataFrame(columns=cols)
    mt = _ns(m1.index)
    dec = mt[hit["k"].to_numpy()[sel]] + 60_000_000_000      # close of the T1 M1 bar
    dt = pd.DatetimeIndex(pd.to_datetime(dec, utc=True))
    out = pd.DataFrame({
        "decision_time": dt, "available_at": dt,
        "direction": bk["dir"].to_numpy()[sel],
        "stop_px": bk["entry"].to_numpy()[sel],               # break even
        "target_px": t2[sel],
    })
    return out.sort_values("decision_time").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("rg02a_t1t2_runner_cisd1h_v1", lambda: detect(cl.load_m1()))
    print("events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=RUNNER_HOLD, claim="+")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "base book: 1h bare CISD (series_open, 2/2 swings, max_wait=3), decide at the "
        "confirming 1h close, enter next M1 open, stop at the protected swing, 10h hold",
        "T1 = nearest confirmed unbroken 1h 2/2 swing high above entry (long) / low below "
        "entry (short), last 200 1h bars, at least 0.25x initial risk from entry",
        "T2 = prior completed NY trading day's high (long) / low (short) at the decision; "
        "keep only trades with T2 beyond T1",
        "scan M1 from entry within the 10h hold: first of stop / T1 (stop wins ties); keep "
        "trades that reach T1 first",
        "event (the runner) at the close of the T1 M1 bar: same direction, stop = original "
        "entry price (break even), target = T2, hold 10h; scored vs matched random entry",
        "the 20% partial at T1 is identical under any variant and is not scored"],
        "params": {"base_tf": "1h", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "base_hold": "10h", "t1": "nearest unbroken 1h swing",
                   "t1_lookback_bars": 200, "min_t1_R": 0.25, "t2": "prior trading day high/low (18:00 NY roll)",
                   "be_stop": "entry price", "runner_hold": RUNNER_HOLD}}
    src = {
        "base_tf": "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked 1h rung-0 book)",
        "level_rule": "phase3: locked config", "swing": "phase3: locked config",
        "max_wait": "phase3: locked config", "base_hold": "phase3: 10 entry-TF bars (§1.13)",
        "t1": "corpus: V8P6lNIisvc 'my T1 is where I'm going to move stops break even'; "
              "yaml: 'T1 := the nearest prior swing low (for a short: high) that the "
              "model's structure targets'",
        "t1_lookback_bars": "declared-before-run: 200 1h bars (~8 sessions) search window",
        "min_t1_R": "declared-before-run: T1 closer than 0.25x initial risk is not a "
                    "structural target (would make the break-even runner's R unit ~0); set "
                    "after seeing only the T1-distance distribution, no outcomes",
        "t2": "declared-before-run: prior day high/low as the higher-timeframe liquidity "
              "objective (yaml: 'T2 := the higher-timeframe liquidity objective')",
        "be_stop": "corpus: V8P6lNIisvc 'move stops break even' (yaml: 'move the stop to "
                   "the entry price')",
        "runner_hold": "declared-before-run: 10h, same as the phase-3 base hold",
    }
    notes = ("Management concept tested as the post-T1 runner leg vs a matched random "
             "control of the same geometry. A NULL means the break-even runner is random "
             "geometry (no momentum after T1), i.e. the scheme reduces variance but does "
             "not add expectancy.")
    p = cl.write_result("t1-t2-partial-system", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print(p)
