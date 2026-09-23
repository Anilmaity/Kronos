"""time-based-exit — hold a position riding an expanding 4H candle to that candle's close.

Concept (sunday_sessions_live_q_a_02): "When a position is riding a higher-timeframe
expansion candle, the close of that candle is a valid exit point, because expansion
candles close at or near their extreme." Detection rules: identify the governing HTF
candle (typically 4H) and its close time; if the candle is expanding in the trade
direction, hold to its close and exit there. Execution: stop behind the protected swing,
exit at the HTF candle close.

Operationalisation (declared before the first run):
  * governing candle: every 4H candle on the forex grid (17/21/01/05/09/13 NY).
  * decision: at the candle's half-way point (open + 2h, the close of its 2nd 1h bar),
    read the running candle (open .. 2nd 1h close) built only from closed 1h bars.
  * "expanding in the trade direction" = running body != 0 and the one-sided opposing run
    (open -> extreme against the body) / |body| <= 1.0 (threshold_fits: small wick =
    expansion candle, grade A cut 1.0).
  * trade: enter next M1 open in the body's direction; stop = the running candle's
    opposing extreme (its protected swing so far); no price target; exit at the 4H
    candle's nominal close (max_hold = open + 4h - decision = 2h wall clock).
  * claim '+': holding in the direction of the expanding candle to its close beats a
    matched random entry (same direction, stop distance, hold). If expansion candles
    really close into their extreme, the real book must beat random geometry.
  * control holds the NY clock (ctrl_tod_tol_min=30): events sit at six fixed clock
    times and the 13:00 candle's hold ends at the 17:00 halt (trap 7/9).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402

CID = "time-based-exit"
WICK_CUT = 1.0
HALF = pd.Timedelta(hours=2)
FULL = pd.Timedelta(hours=4)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    b1 = cl.build_bars(m1, "1h")
    b4 = cl.build_bars(m1, "4h")
    if b1.empty or b4.empty:
        return pd.DataFrame(columns=cols)
    s4n = pd.DatetimeIndex(b4.index).tz_convert("UTC").as_unit("ns").asi8
    t1 = pd.DatetimeIndex(b1.index).tz_convert("UTC").as_unit("ns")
    k = np.searchsorted(s4n, t1.asi8, side="right") - 1          # 4H bucket of each 1h bar
    valid = k >= 0
    start = np.full(len(b1), np.iinfo(np.int64).min)
    start[valid] = s4n[k[valid]]
    rel = t1.asi8 - start
    half_ns = HALF.value
    use = valid & (rel >= 0) & (rel < half_ns)                   # 1h bars in the first half
    df = pd.DataFrame({"k": k[use], "open": b1["open"].to_numpy()[use],
                       "high": b1["high"].to_numpy()[use], "low": b1["low"].to_numpy()[use],
                       "close": b1["close"].to_numpy()[use],
                       "ct": pd.DatetimeIndex(b1["close_time"]).tz_convert("UTC").as_unit("ns")[use].asi8})
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = df.groupby("k", sort=True)
    agg = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last(),
                        "ct": g["ct"].max()})
    bstart = s4n[agg.index.to_numpy()]
    dec = bstart + half_ns
    agg = agg[agg["ct"].to_numpy() == dec]                       # the 2nd 1h bar closed at +2h
    bstart = s4n[agg.index.to_numpy()]
    body = agg["close"].to_numpy() - agg["open"].to_numpy()
    sgn = np.sign(body)
    opp = np.where(sgn > 0, agg["open"] - agg["low"], agg["high"] - agg["open"])
    keep = (sgn != 0) & (opp <= WICK_CUT * np.abs(body))
    agg, sgn, bstart = agg[keep], sgn[keep].astype(int), bstart[keep]
    dt = pd.to_datetime(bstart + half_ns, utc=True)
    out = pd.DataFrame({
        "decision_time": dt,
        "available_at": pd.to_datetime(agg["ct"].to_numpy(), utc=True),
        "direction": sgn,
        "stop_px": np.where(sgn > 0, agg["low"], agg["high"]).astype(float),
        "target_px": np.nan,
        "max_hold": pd.to_timedelta(np.full(len(agg), (FULL - HALF).value), unit="ns"),
    })
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("tbe_4h_half_smallwick1.0_hold_to_close", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, claim="+", ctrl_tod_tol_min=30)
    print({k: res.get(k) for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "verdict", "verdict_detail", "exposure_bars",
                                   "ties", "ctrl_overlap", "halves", "exit_mix")})
    op = {"rules": [
        "governing candle: 4H, forex grid 17/21/01/05/09/13 NY",
        "decide at the 4H open + 2h (close of its 2nd 1h bar); running candle = first two "
        "closed 1h bars of the 4H bucket",
        "expanding = body != 0 and opposing run (open->extreme against the body) / |body| <= 1.0",
        "enter next M1 open in the body's direction; stop = running candle's opposing extreme; "
        "no price target; exit at the 4H candle's nominal close (2h after the decision)",
        "claim '+': beats matched random entry (same direction, stop distance, 2h hold, "
        "NY clock within 30 min)"],
        "params": {"htf": "4h", "grid4h": "forex", "decision_offset": "2h",
                   "wick_cut": WICK_CUT, "hold": "to 4H close (2h)", "ctrl_tod_tol_min": 30}}
    src = {"htf": "corpus: time-based-exit 'Identify the governing HTF candle (typically 4H)'",
           "grid4h": "phase3: 4H grid carried as a knob; forex grid is the locked default "
                     "(session_window_fit §1.4)",
           "decision_offset": "declared-before-run: the corpus gives no entry point inside "
                              "the candle; the half-way close is the earliest point with two "
                              "closed 1h bars to classify the candle",
           "wick_cut": "threshold_fits: small wick / expansion candle opposing_run/|body| <= "
                       "1.0 (grade A)",
           "hold": "corpus: time-based-exit 'hold to its close and exit there'",
           "ctrl_tod_tol_min": "declared-before-run: README trap 7/9, events at six fixed "
                               "clock times and holds that end at the 17:00 NY halt"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="The corpus's trailed stop ('trail behind the protected swing') "
                              "is held fixed at the running candle's extreme: the harness "
                              "has no stop modification. No structural target is used, "
                              "because the corpus names none and leaves precedence unstated.")
    print("wrote", p)
