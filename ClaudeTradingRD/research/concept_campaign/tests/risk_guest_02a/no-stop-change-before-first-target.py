"""no-stop-change-before-first-target (guest: AM Trades) — batch risk_guest_02a.

Claim tested: before the first target is hit, an adverse structure shift carries no
information against the position, so the original bracket (original stop, target
T1) should be kept "regardless of what the market shows". Operationally: at the
moment an adverse structure shift prints on an open position, holding the original
stop / T1 bracket for the rest of the hold does at least as well as a matched random
entry with the same geometry. claim '+': the held position beats random geometry;
NEGATIVE would mean the shift predicts failure, i.e. moving the stop / exiting would
have helped (the concept's measurable: "expectancy of never-move-before-T1 vs moving
on an adverse structure shift").

Base entry model: 1h bare CISD with T1 = nearest unbroken 1h swing (see _base_cisd.py).
Adverse structure shift (long; mirrored for short): after entry, the first 15m bar
that CLOSES below the most recent confirmed 15m 2/2 swing low, while that swing low is
above the original stop and the position is still open (neither stop nor T1 touched on
M1 up to that bar's close) and inside the base 10h hold.
Event at that 15m close: same direction, stop_px = original stop, target_px = T1,
max_hold = what remains of the base 10h hold.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402
from _base_cisd import base_book, first_stop_or_t1, _ns  # noqa: E402

MIN_REMAIN = pd.Timedelta("15min")


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px",
            "max_hold"]
    bk = base_book(m1)
    if bk.empty:
        return pd.DataFrame(columns=cols)
    hit = first_stop_or_t1(m1, bk)
    mt = _ns(m1.index)
    # time by which the position is closed by stop/T1 (close of that M1 bar), else end
    k = hit["k"].to_numpy()
    closed_ns = np.where(k >= 0, mt[np.maximum(k, 0)] + 60_000_000_000,
                         np.iinfo(np.int64).max)

    b15 = cl.build_bars(m1, "15min")
    o15 = b15[["open", "high", "low", "close"]]
    sw = swing_points(o15, left=2, right=2)
    c_ns = _ns(b15["close_time"])
    s_ns = _ns(b15.index)
    C = b15["close"].to_numpy(float)
    H = b15["high"].to_numpy(float)
    L = b15["low"].to_numpy(float)
    n = len(b15)
    conf = np.full(n, np.iinfo(np.int64).max, dtype=np.int64)
    conf[: max(0, n - 2)] = c_ns[2:]
    ih = np.nonzero(sw["swing_high"].to_numpy())[0]
    il = np.nonzero(sw["swing_low"].to_numpy())[0]
    conf_h, conf_l = conf[ih], conf[il]
    # conf is monotone in the swing index, so "most recent confirmed swing at time t"
    # = the last swing whose confirmation close <= t
    rows = []
    for r, row in enumerate(bk.itertuples(index=False)):
        entry_start = mt[int(row.i0)]
        m0 = int(np.searchsorted(s_ns, entry_start, side="left"))
        end_ns = min(int(row.hold_end_ns), int(closed_ns[r]))
        m = m0
        while m < n and c_ns[m] <= end_ns:
            if c_ns[m] > int(closed_ns[r]) - 1 and closed_ns[r] != np.iinfo(np.int64).max:
                break
            t = c_ns[m]
            if row.dir == 1:
                q = int(np.searchsorted(conf_l, t, side="right")) - 1
                if q >= 0:
                    lvl = L[il[q]]
                    if lvl > row.stop and C[m] < lvl:
                        rows.append((t, row.dir, row.stop, row.t1,
                                     int(row.hold_end_ns) - t))
                        break
            else:
                q = int(np.searchsorted(conf_h, t, side="right")) - 1
                if q >= 0:
                    lvl = H[ih[q]]
                    if lvl < row.stop and C[m] > lvl:
                        rows.append((t, row.dir, row.stop, row.t1,
                                     int(row.hold_end_ns) - t))
                        break
            m += 1
    if not rows:
        return pd.DataFrame(columns=cols)
    a = np.array(rows, dtype=object)
    dt = pd.DatetimeIndex(pd.to_datetime(a[:, 0].astype(np.int64), utc=True))
    out = pd.DataFrame({
        "decision_time": dt, "available_at": dt,
        "direction": a[:, 1].astype(int),
        "stop_px": a[:, 2].astype(float), "target_px": a[:, 3].astype(float),
        "max_hold": pd.to_timedelta(a[:, 4].astype(np.int64), unit="ns"),
    })
    out = out[out["max_hold"] >= MIN_REMAIN]
    return out.sort_values("decision_time").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("rg02a_nostopchange_cisd1h_v1", lambda: detect(cl.load_m1()))
    print("events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, claim="+")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "base book: 1h bare CISD (series_open, 2/2 swings, max_wait=3), decide at the "
        "confirming 1h close, enter next M1 open, stop at the protected swing, 10h hold",
        "first target T1 = nearest confirmed unbroken 1h 2/2 swing beyond entry (last 200 "
        "1h bars), at least 0.25x initial risk from entry",
        "adverse structure shift = first 15m close (bars starting at/after entry) through "
        "the most recent confirmed 15m 2/2 swing low (long) / high (short) that lies "
        "between the original stop and price, while no stop/T1 touch has occurred on M1",
        "event at that 15m close: keep the original bracket (stop = original stop, target "
        "= T1), max_hold = remainder of the 10h base hold (>= 15 min)",
        "scored vs matched random entry with the same stop/target distances and hold"],
        "params": {"base_tf": "1h", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "base_hold": "10h", "t1": "nearest unbroken 1h swing",
                   "t1_lookback_bars": 200, "min_t1_R": 0.25,
                   "shift_tf": "15min", "shift_swing": "2/2", "min_remaining_hold": "15min"}}
    src = {
        "base_tf": "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked 1h rung-0 book)",
        "level_rule": "phase3: locked config", "swing": "phase3: locked config",
        "max_wait": "phase3: locked config", "base_hold": "phase3: 10 entry-TF bars (§1.13)",
        "t1": "declared-before-run: 'first target' is undefined in CrUfTskOveo; use the "
              "related t1-t2-partial-system corpus definition (nearest prior swing extreme)",
        "t1_lookback_bars": "declared-before-run: 200 1h bars search window",
        "min_t1_R": "declared-before-run: T1 closer than 0.25x initial risk is not a target",
        "shift_tf": "declared-before-run: 15m, one step below the 1h entry TF (the phase-3 "
                    "15m/1H stack pairing)",
        "shift_swing": "phase3: 2/2 fractal swings as in the locked config",
        "min_remaining_hold": "declared-before-run: drop shifts with <15 min of hold left",
    }
    notes = ("Corpus: CrUfTskOveo 'if i'm not hitting my first target i'm not touching my "
             "stop'. Tested as: at an adverse 15m structure shift before T1, does the held "
             "original bracket beat random geometry. NEGATIVE would support moving the "
             "stop on the shift; NULL means the shift is uninformative (holding costs "
             "nothing vs reacting).")
    p = cl.write_result("no-stop-change-before-first-target", None, res,
                        operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes=notes)
    print(p)
