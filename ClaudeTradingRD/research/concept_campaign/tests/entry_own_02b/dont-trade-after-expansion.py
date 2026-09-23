"""dont-trade-after-expansion (contested) — batch entry_own_02b.

reading a (4Gm8p6O7Ebs / FKTBkTzsmUA / PQiRV0JMhIQ): "After 3 days of expansion, I
don't want to trade in the same direction." Baseline = phase-3 rung-0 1h CISD book.
Gate = the last THREE completed daily candles (18:00 NY roll) each CLOSED beyond the
previous day's extreme in the trade's direction (expansion = close beyond the level,
the grade-A structural test). claim '-': those continuation entries do worse.

reading b (Py_dwGcTCTM): "stop entering at the end of higher time frame candles".
Baseline = phase-3 rung-0 5m CISD book (5m is the 1h's paired entry TF). Gate = at the
decision the current 1h candle has ALREADY expanded in the trade direction (traded
beyond the previous 1h candle's high for a long / low for a short) AND at least 20 of
its 60 minutes have elapsed (continuation-timing: "40 minutes left in an hourly candle"
is the worked rejection). claim '-'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                    # noqa: E402
from detectors.cisd import cisd_events                      # noqa: E402
from _common import ns, ONE_MIN                             # noqa: E402

N_DAYS = 3
LATE_MIN = 20
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "rr", "after_3exp"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr", "late_expanded"]


def _cisd_book(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=["decision_time", "available_at", "direction", "stop_px", "rr"])
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    last_ok = m1.index[-1] + pd.Timedelta("1min")
    keep = np.asarray(close <= last_ok)
    return pd.DataFrame({"decision_time": close[keep], "available_at": close[keep],
                         "direction": np.where(ev["direction"] == "bullish", 1, -1)[keep],
                         "stop_px": ev["protected_swing"].to_numpy()[keep], "rr": 2.0})


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 3000:
        return pd.DataFrame(columns=COLS_A)
    ev = _cisd_book(m1, "1h")
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] > 300]
    h, l, c = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    up = np.zeros(len(d), bool)
    dn = np.zeros(len(d), bool)
    up[1:] = c[1:] > h[:-1]
    dn[1:] = c[1:] < l[:-1]
    run_up = pd.Series(up).groupby((~pd.Series(up)).cumsum()).cumsum().to_numpy()
    run_dn = pd.Series(dn).groupby((~pd.Series(dn)).cumsum()).cumsum().to_numpy()
    dd = pd.DataFrame({"run_up": run_up, "run_dn": run_dn,
                       "close_time": d["close_time"].to_numpy()}, index=d.index)
    z = cl.asof(dd, pd.DatetimeIndex(ev["decision_time"]))
    ru = z["run_up"].fillna(0).to_numpy()
    rd = z["run_dn"].fillna(0).to_numpy()
    dirn = ev["direction"].to_numpy()
    ev["after_3exp"] = np.where(dirn == 1, ru >= N_DAYS, rd >= N_DAYS)
    return ev.reset_index(drop=True)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 3000:
        return pd.DataFrame(columns=COLS_B)
    ev = _cisd_book(m1, "5min")
    t = ns(m1.index)
    hour = np.int64(60) * ONE_MIN
    hid = t // hour
    hi = pd.Series(m1["high"].to_numpy()).groupby(hid).cummax().to_numpy()
    lo = pd.Series(m1["low"].to_numpy()).groupby(hid).cummin().to_numpy()
    hb = cl.build_bars(m1, "1h")
    dec = ns(ev["decision_time"])
    start = (dec // hour) * hour
    elapsed_min = (dec - start) // ONE_MIN
    k = np.searchsorted(t, dec, "left") - 1                   # last M1 bar starting before t
    same = (k >= 0) & (t[np.clip(k, 0, None)] >= start)
    run_hi = np.where(same, hi[np.clip(k, 0, None)], np.nan)
    run_lo = np.where(same, lo[np.clip(k, 0, None)], np.nan)
    prev = cl.asof(hb, pd.DatetimeIndex(start).tz_localize("UTC"))   # last 1h bar closed by the hour start
    ph, pl = prev["high"].to_numpy(float), prev["low"].to_numpy(float)
    dirn = ev["direction"].to_numpy()
    expanded = np.where(dirn == 1, run_hi > ph, run_lo < pl)
    expanded = np.where(np.isnan(run_hi) | np.isnan(ph), False, expanded)
    ev["late_expanded"] = expanded & (elapsed_min >= LATE_MIN)
    return ev.reset_index(drop=True)


OP_A = {"rules": [
    "baseline: 1h bare CISD (series_open, 2/2, max_wait 3), decide at confirm close, stop protected swing, 2R, 10h",
    "expansion day = a daily (18:00 NY) candle CLOSING above the previous day's high (bull) / below its low (bear); "
    "stub days (<=300 M1) skipped",
    "gate: the last 3 completed days are consecutive expansion days in the trade's direction (read via cl.asof)"],
    "params": {"n_days": N_DAYS, "baseline": "1h rung-0 CISD", "max_hold": "10h", "day_open_hour": 18}}
OP_B = {"rules": [
    "baseline: 5m bare CISD (series_open, 2/2, max_wait 3), decide at confirm close, stop protected swing, 2R, 50min",
    "gate: at the decision the in-progress UTC-hour 1h candle has already traded beyond the previous 1h candle's high "
    "(long) / low (short), from M1 up to the decision, AND >= 20 minutes of it have elapsed"],
    "params": {"late_min": LATE_MIN, "baseline": "5m rung-0 CISD", "max_hold": "50min", "htf": "1h"}}
SRC = {"n_days": "corpus: FKTBkTzsmUA 'After 3 days of expansion, I don't want to trade in the same direction'",
       "baseline": "phase3: rung-0 CISD book (locked config)",
       "max_hold": "phase3: 10 entry-TF bars",
       "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
       "late_min": "corpus: continuation-timing (method_spec §4.5) 'The worked rejection: 40 minutes left in an hourly candle'",
       "htf": "method_spec: §1.2 pairing 1-hour -> 5-minute"}

if __name__ == "__main__":
    todo = sys.argv[1:] or ["a", "b"]
    for rd, fn, op, col, mh, key in (("a", detect_a, OP_A, "after_3exp", "10h", "dtae_a_1h_3d"),
                                     ("b", detect_b, OP_B, "late_expanded", "50min", "dtae_b_5m_late20")):
        if rd not in todo:
            continue
        ev = cl.cache_frame(key, lambda fn=fn: fn(cl.load_m1()))
        print(rd, len(ev), ev[col].mean())
        probe = cl.probe_lookahead(fn, ev, lookback="20D")
        print("probe", probe.get("passed"))
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=mh, claim="-")
        print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
                                       "ties", "ctrl_overlap", "sanity")})
        cl.write_result("dont-trade-after-expansion", rd, res, operationalization=op,
                        params_source={k: SRC[k] for k in op["params"]}, script=__file__, probe=probe,
                        notes=("Reading a: 3-day expansion stand-aside, gate on 1h CISD continuations; complement = all "
                               "other 1h CISD trades (incl. counter-streak)." if rd == "a" else
                               "Reading b: 'end of an HTF expansion candle' = current 1h candle already beyond the prior "
                               "1h extreme in the trade direction with <=40 min left; baseline 5m CISD."))
