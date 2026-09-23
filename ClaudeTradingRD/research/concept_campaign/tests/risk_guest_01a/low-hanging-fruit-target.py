"""low-hanging-fruit-target (guest: DTR) - trade_test.

Concept: target the nearest obvious session level in the trade's direction - Asia
high/low, London high/low, the New York session open, or the previous day's high/low -
aiming for roughly 2-2.5R; if the nearest level does not offer roughly 2R, one example
accepted a slightly closer level, another skipped to the further one; cross-check the
target against the remaining average daily range. No stop rule is given, so the
baseline's stop is used.

Operationalisation (declared before run):
  entries  : every 15m bare CISD (phase-3 rung-0 config), stop at the protected swing,
             decided at the confirming 15m close (reference price = that close)
  levels   : last completed Asia (20:00-00:00 NY) and London (02:00-05:00 NY) session
             high/low, today's 08:30 NY open, previous trading day's high/low (stub days
             skipped: min_coverage 0.5) - all known at the decision
  target   : walk outward from the reference through the levels strictly beyond it in
             the trade's direction; take the first whose distance is >= 1.5 x the stop
             distance ("slightly closer accepted"; nearer ones are skipped). If that
             level is > 3.0R away there is no low-hanging fruit: no trade.
  ADR check: the target distance must not exceed the remaining ADR = mean range of the
             last 5 completed trading days minus today's range so far; else no trade.
  exit     : stop, the level, or 150 minutes.
claim '+': the level-targeted book beats a matched random entry with the same stop and
target distances. Because bare CISD entries are null against their control (phase 3),
the differential isolates what the session-level target adds over the same geometry.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl   # noqa: E402
import _book as bk         # noqa: E402
from concept_lab.data import utc_ns   # noqa: E402

CID = "low-hanging-fruit-target"
RR_MIN, RR_MAX = 1.5, 3.0
ADR_N = 5
NY_OPEN = "08:30"
TOD_TOL = 30


def detect(m1):
    raw = bk.raw_cisd(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    if raw.empty:
        return pd.DataFrame(columns=cols)
    d = pd.DatetimeIndex(raw["decision_time"])
    tn = utc_ns(m1.index)
    pos = np.searchsorted(tn, utc_ns(d), side="left") - 1      # last M1 bar closed by d
    ok = pos >= 0
    ref = np.where(ok, m1["close"].to_numpy(float)[np.clip(pos, 0, None)], np.nan)
    sgn = raw["direction"].to_numpy(np.int64)
    stop = raw["stop_px"].to_numpy(float)
    risk = sgn * (ref - stop)
    lv = []
    for w in ("asia", "london"):
        h = cl.prior_hilo(d, w, m1=m1)
        lv += [h["high"].to_numpy(float), h["low"].to_numpy(float)]
    pd1 = cl.prior_hilo(d, "1D", m1=m1, min_coverage=0.5)
    lv += [pd1["high"].to_numpy(float), pd1["low"].to_numpy(float)]
    lv.append(cl.open_at(d, NY_OPEN, m1=m1)["price"].to_numpy(float))
    L = np.vstack(lv).T                                   # (n, 7), NaN = unavailable
    dist = sgn[:, None] * (L - ref[:, None])              # > 0: beyond, in direction
    dist = np.where(np.isfinite(dist) & (dist > 0), dist, np.inf)
    rr = dist / risk[:, None]
    rr_ok = np.where(rr >= RR_MIN, rr, np.inf)
    pick_rr = rr_ok.min(axis=1)                           # first level >= 1.5R outward
    # ADR remaining
    rngs = []
    for nb in range(1, ADR_N + 1):
        h = cl.prior_hilo(d, "1D", n_back=nb, m1=m1, min_coverage=0.5)
        rngs.append((h["high"] - h["low"]).to_numpy(float))
    adr = np.vstack(rngs).mean(axis=0)
    run = cl.running_hilo(d, "1D", m1=m1)
    today = (run["high"] - run["low"]).to_numpy(float)
    remaining = adr - today
    tgt_dist = pick_rr * risk
    keep = (ok & np.isfinite(risk) & (risk > 0) & np.isfinite(pick_rr)
            & (pick_rr <= RR_MAX) & np.isfinite(remaining) & (tgt_dist <= remaining))
    out = pd.DataFrame({"decision_time": d[keep], "available_at": d[keep],
                        "direction": sgn[keep], "stop_px": stop[keep],
                        "target_px": (ref + sgn * tgt_dist)[keep]})
    return out.reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{RR_MIN}_{RR_MAX}_{ADR_N}_{NY_OPEN}",
                        lambda: detect(cl.load_m1()), version=bk.VERSION)
    print(len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold="150min", ctrl_tod_tol_min=TOD_TOL, claim="+")
    for k in ("n", "avg_R", "avg_R_gross", "win_rate", "diff", "ci_lo", "ci_hi", "p",
              "mde", "verdict", "verdict_detail", "exposure_bars", "ties", "dropped",
              "exit_mix"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "entries: 15m bare CISD (series_open, 2/2 swings, max_wait 3), decided at the "
        "confirming bar's close, next-M1-open entry, stop at the protected swing",
        "levels known at the decision: last completed Asia (20:00-00:00 NY) and London "
        "(02:00-05:00 NY) high/low, today's 08:30 NY open, previous trading day's "
        "high/low (min_coverage 0.5)",
        f"target: nearest level beyond the decision close in the trade's direction whose "
        f"distance is >= {RR_MIN}x the stop distance (nearer levels skipped); no trade if "
        f"that level is > {RR_MAX}R",
        f"ADR check: target distance <= mean range of the last {ADR_N} completed trading "
        "days minus today's range so far; else no trade",
        "exit: stop, level, or 150 minutes"],
        "params": {"baseline_tf": bk.TF, "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "max_hold": "150min", "rr_min": RR_MIN, "rr_max": RR_MAX,
                   "adr_days": ADR_N, "ny_open": NY_OPEN, "asia_window": "20:00-00:00",
                   "london_window": "02:00-05:00", "pdh_min_coverage": 0.5,
                   "ctrl_tod_tol_min": TOD_TOL}}
    src = {"baseline_tf": bk.BASE_SOURCES["baseline_tf"],
           "level_rule": bk.BASE_SOURCES["level_rule"], "swing": bk.BASE_SOURCES["swing"],
           "max_wait": bk.BASE_SOURCES["max_wait"], "max_hold": bk.BASE_SOURCES["max_hold"],
           "rr_min": "declared-before-run: yaml 'aiming for roughly 2 to 2.5R', 'one "
                     "example accepted a slightly closer level'",
           "rr_max": "declared-before-run: beyond 3R the nearest acceptable level is not "
                     "'low hanging' (yaml 2-2.5R)",
           "adr_days": "declared-before-run: yaml 'cross-check against the remaining "
                       "average daily range' gives no length; 5 days",
           "ny_open": "session_window_fit: ny_am session opens 08:30 NY (method spec 2.5)",
           "asia_window": "session_window_fit: SESSION_WINDOWS asia 20:00-00:00 NY",
           "london_window": "session_window_fit: SESSION_WINDOWS london 02:00-05:00 NY",
           "pdh_min_coverage": "declared-before-run: skip stub sessions (README trap 6)",
           "ctrl_tod_tol_min": "declared-before-run: targets depend on session levels, "
                               "so hold the NY clock in the control (README trap 9)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="DTR gives no stop rule; the CISD protected swing is used. "
                              "Levels are the guest's list verbatim; the 08:30 NY open "
                              "is gold's NY session open (DTR trades indices, 09:30).")
    print(p)
