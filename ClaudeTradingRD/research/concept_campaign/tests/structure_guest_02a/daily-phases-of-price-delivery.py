"""daily-phases-of-price-delivery (guest: AM Trades, QmGJFxfSHxM) -> rate_test.

Claim: "an expansion is never immediately followed by another expansion" - after a
large-range expansion day an intermediate phase (retracement / reversal / consolidation)
must come first. First measurable: "frequency with which two large-range same-direction
expansion days occur back to back (the rule says this should be rare)". claim '-': the
day after an expansion day is a same-direction expansion day LESS often than a matched
random day's next day.

Reading (declared before the first run):
  * Daily candles on the 18:00 NY roll; stub sessions (< 600 M1 bars) are skipped.
  * Expansion day := range >= 1.5 x the mean range of the 20 days ending TWO days earlier
    (the benchmark skips the prior day, so a big day never inflates the next day's own
    benchmark - no mechanical bias toward the claim) AND small opposing run:
    opposing_run / |body| <= 1.0 (bullish: open - low; bearish: high - open).
    Direction = sign(close - open).
  * Event = every expansion day; outcome = the next trading day is an expansion day in the
    same direction.
  * Null: for each event, a random day within +/-21 trading days (5 reps, seeded); outcome
    = that day's NEXT day is an expansion day in the event's direction (the unconditional
    local rate of a same-direction expansion day).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402

CID = "daily-phases-of-price-delivery"
MIN_M1 = 600
BENCH_N = 20
R_MULT = 1.5
WICK_BODY = 1.0
NULL_WIN = 21


def classify(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] > MIN_M1].copy()
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    rng_ = h - l
    bench = pd.Series(rng_).shift(2).rolling(BENCH_N, min_periods=BENCH_N).mean().to_numpy()
    body = np.abs(c - o)
    sgn = np.sign(c - o)
    opp = np.where(sgn > 0, o - l, h - o)
    with np.errstate(divide="ignore", invalid="ignore"):
        exp_ = (rng_ >= R_MULT * bench) & (body > 0) & (opp / body <= WICK_BODY)
    exp_dir = np.where(exp_ & np.isfinite(bench), sgn, 0).astype(int)
    return pd.DataFrame({"close_time": pd.DatetimeIndex(d["close_time"]),
                         "exp_dir": exp_dir, "bench_ok": np.isfinite(bench)})


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    k = classify(m1)
    e = k[k["exp_dir"] != 0]
    return pd.DataFrame({"decision_time": pd.DatetimeIndex(e["close_time"]),
                         "available_at": pd.DatetimeIndex(e["close_time"]),
                         "direction": e["exp_dir"].astype(int).to_numpy()}).reset_index(drop=True)


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"{CID}_r{R_MULT}_b{BENCH_N}_w{WICK_BODY}", lambda: detect(cl.load_m1()))
    k = classify(m1)
    pos_of = {t: i for i, t in enumerate(pd.DatetimeIndex(k["close_time"]).asi8)}
    pos = np.array([pos_of[t] for t in pd.DatetimeIndex(ev["decision_time"]).asi8])
    keep = pos + 1 < len(k)
    ev = ev[keep].reset_index(drop=True)
    pos = pos[keep]
    # the probe must see the frame that is tested -> probe after trimming the last day
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    ed = k["exp_dir"].to_numpy()
    dirs = ev["direction"].to_numpy()
    obs = (ed[pos + 1] == dirs).astype(float)
    print("events", len(ev), "obs rate", obs.mean(), "base exp rate", (ed != 0).mean())
    N = len(k)

    def null_fn(rng, kk):
        off = rng.integers(1, NULL_WIN + 1, len(pos)) * rng.choice([-1, 1], len(pos))
        q = np.clip(pos + off, 0, N - 2)
        return (ed[q + 1] == dirs).astype(float)

    t = pd.DatetimeIndex(ev["decision_time"])
    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="-", predictors=ev,
                       outcome_horizon="2D")
    for kk in ("n", "rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
               "verdict_detail", "halves"):
        print(kk, res.get(kk))
    op = {"rules": [
        "daily candles (18:00 NY roll), stub sessions < 600 M1 bars skipped",
        "expansion day: range >= 1.5 x mean range of the 20 days ending two days earlier, "
        "and opposing_run/|body| <= 1.0; direction = sign(close-open)",
        "event = expansion day; hit = the next trading day is a same-direction expansion day",
        "null = next day of a random day within +/-21 trading days is an expansion day in the "
        "event's direction (5 seeded reps)"],
        "params": {"r_mult": R_MULT, "bench_n": BENCH_N, "wick_body": WICK_BODY,
                   "min_m1": MIN_M1, "null_win_days": NULL_WIN}}
    src = {"r_mult": "threshold_fits: displacement magnitude r=1.5 (range vs pre-range, grade B)",
           "bench_n": "threshold_fits: trailing 20-window convention (displacement_fire_rate "
                      "trailing median of 20)",
           "wick_body": "threshold_fits: small wick / expansion candle opposing_run/|body| <= 1.0 "
                        "(grade A; 'Candles that support expansion will have a small wick and a "
                        "large body')",
           "min_m1": "declared-before-run: stub-session filter as in the concept_lab rate example",
           "null_win_days": "declared-before-run: +/-21 trading days ~ the locked +/-30 calendar "
                            "day control window"}
    notes = ("Benchmark skips the prior day so an expansion day does not raise its successor's "
             "threshold (that would bias toward the claim). Only the back-to-back frequency claim "
             "is tested; the weekly 'opening days' trade rules need an undefined real-time phase "
             "classifier.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
