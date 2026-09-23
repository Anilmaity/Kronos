"""three-entry-quality-criteria — gate_test on the phase-3 bare 15m CISD book.

Claim (+): entries meeting >= 2 of the 3 criteria (targets not yet hit, daily range
not yet created, entry near the daily open) beat entries meeting <= 1.
All parameters declared before the first run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, cisd_book, day_context, run_and_print, PHASE3_SRC  # noqa: E402

TF = "15min"
N_DAYS = 5          # expected daily range = mean of last 5 completed days
BULK = 0.5          # "bulk of the range produced" = realised range >= 50% of expected
NEAR_OPEN = 0.25    # "near the daily open" = |price - day open| <= 0.25 x expected range
MIN_SCORE = 2       # 3/3 good, 2/3 acceptable -> gated; 1/3, 0/3 -> complement
MAX_HOLD = "150min"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    ev = cisd_book(m1, TF)
    if ev.empty:
        return ev.assign(score=pd.Series(dtype=float), quality=pd.Series(dtype=bool))
    ctx = day_context(m1, ev["decision_time"], n_days=N_DAYS)
    d = ev["direction"].to_numpy()
    px = ev["confirm_close"].to_numpy()
    long = d == 1
    # C1: the directional target (PDH for longs, PDL for shorts) not yet taken today
    c1 = np.where(long, ctx["run_hi"].to_numpy() < ctx["pdh"].to_numpy(),
                  ctx["run_lo"].to_numpy() > ctx["pdl"].to_numpy())
    # C2: bulk of the expected daily range not yet produced
    realised = ctx["run_hi"].to_numpy() - ctx["run_lo"].to_numpy()
    c2 = realised < BULK * ctx["exp_range"].to_numpy()
    # C3: entry near the daily (18:00 NY) open
    c3 = np.abs(px - ctx["day_open"].to_numpy()) <= NEAR_OPEN * ctx["exp_range"].to_numpy()
    valid = np.isfinite(ctx[["day_open", "run_hi", "run_lo", "pdh", "pdl",
                             "exp_range"]].to_numpy()).all(axis=1)
    ev = ev.assign(c1=c1, c2=c2, c3=c3)[valid].reset_index(drop=True)
    ev["score"] = ev[["c1", "c2", "c3"]].sum(axis=1).astype(float)
    ev["quality"] = ev["score"] >= MIN_SCORE
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"teqc_{TF}_n{N_DAYS}_b{BULK}_o{NEAR_OPEN}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["score"].value_counts().sort_index().to_dict(),
          ev[["c1", "c2", "c3"]].mean().round(3).to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "quality", mask_available_at="decision_time", max_hold=MAX_HOLD)
    run_and_print(res)
    op = {"rules": [
        "baseline book: phase-3 bare 15m CISD (series_open, 2/2 swings, max_wait 3, min_series 1), "
        "decide at confirming bar close, enter next M1 open, stop = protected swing, 2R, hold 150min",
        "C1 targets not hit: long -> today's running high (M1 closed by t) < PDH; short -> running low > PDL",
        "C2 range not created: today's running high-low < 0.5 x mean range of last 5 completed days (>=600 M1 bars)",
        "C3 near daily open: |confirm close - today's 18:00 NY open| <= 0.25 x that expected range",
        "gate: score = C1+C2+C3 >= 2 (3/3 good, 2/3 acceptable) vs <= 1 (poor / low probability)"],
        "params": {"tf": TF, "n_days": N_DAYS, "bulk": BULK, "near_open": NEAR_OPEN,
                   "min_score": MIN_SCORE, "max_hold": MAX_HOLD, "day_open_hour": 18,
                   "target_ref": "gold's own PDH/PDL", "min_day_m1": 600}}
    src = {"tf": "phase3: primary entry TF 15m (concept ltf 15m/5m)",
           "max_hold": PHASE3_SRC + " — 10 entry-TF bars",
           "n_days": "declared-before-run: 'the last several daily candles' -> 5 (one trading week)",
           "bulk": "declared-before-run: 'bulk of the expected range' -> half",
           "near_open": "declared-before-run: 'around the daily open', no tolerance in corpus -> a quarter of the expected range",
           "min_score": "corpus: 0AYGNc9czYc grading '3/3 good, 2/3 acceptable, 1/3 poor, 0/3 low probability'",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "target_ref": "declared-before-run: correlated-asset targets replaced by gold's own PDH/PDL (single instrument)",
           "min_day_m1": "declared-before-run: skip stub days (trap 6)"}
    notes = ("Filter concept tested as a gate on the phase-3 15m CISD book (the directional idea). "
             "Correlated-asset targets are replaced by gold's own previous-day extremes. "
             "Rows lacking any daily context are dropped before scoring (never-evaluated != failed).")
    p = cl.write_result("three-entry-quality-criteria", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print("wrote", p)
