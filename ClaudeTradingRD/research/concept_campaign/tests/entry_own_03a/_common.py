"""Shared helpers for batch entry_own_03a (pure functions of the M1 input)."""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                       # noqa: E402
from detectors.cisd import cisd_events         # noqa: E402

PY = "/Users/anil/Projects/Kronos/ClaudeTradingRD/.venv/bin/python"

# phase-3 locked CISD configuration (conjunction_preregistration §1.8-1.13)
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
PHASE3_SRC = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked primary config)"


def cisd_book(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Bare phase-3 CISD on `tf`: decide at the confirming bar's close, stop at the
    protected swing, 2R. Extra columns: confirm_close, extreme_time (bar start)."""
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], **CISD_KW)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "confirm_close"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
        "confirm_close": ev["confirm_close"].to_numpy(float),
    })
    # a confirming bar whose close is already beyond the stop cannot be traded
    ok = (out["direction"] * (out["confirm_close"] - out["stop_px"])) > 0
    return out[ok].reset_index(drop=True)


def last_m1_day(times) -> pd.DatetimeIndex:
    """Trading day of the last M1 bar CLOSED by t (i.e. the bar starting at t-1min)."""
    t = pd.DatetimeIndex(times).tz_convert("UTC")
    return cl.trading_day(t - pd.Timedelta(minutes=1))


def day_context(m1: pd.DataFrame, times, n_days: int = 5, min_m1: int = 600
                ) -> pd.DataFrame:
    """Per decision time t (all inputs closed by t):
    day_open   open of the first M1 bar of t's trading day (18:00 NY roll)
    run_hi/lo  high/low of that trading day so far (M1 bars closed by t)
    pdh/pdl    previous COMPLETED trading day with >= min_m1 M1 bars
    exp_range  mean high-low of the last n_days completed days with >= min_m1 bars
    """
    t = pd.DatetimeIndex(times).tz_convert("UTC")
    # --- current day open and running extremes, from M1 closed by t
    td_m1 = cl.trading_day(m1.index)
    first_open = pd.Series(m1["open"].to_numpy(), index=td_m1).groupby(level=0).first()
    tday = last_m1_day(t)
    day_open = first_open.reindex(tday).to_numpy(float)
    rh = cl.running_hilo(t, "1D", m1=m1)
    # --- completed days
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= min_m1].copy()
    d["rng"] = d["high"] - d["low"]
    d["exp_range"] = d["rng"].rolling(n_days, min_periods=n_days).mean()
    a = cl.asof(d, t)
    return pd.DataFrame({
        "day_open": day_open,
        "run_hi": rh["high"].to_numpy(float), "run_lo": rh["low"].to_numpy(float),
        "pdh": a["high"].to_numpy(float), "pdl": a["low"].to_numpy(float),
        "pd_close_time": pd.DatetimeIndex(a["close_time"]),
        "exp_range": a["exp_range"].to_numpy(float),
    }, index=t)


def run_and_print(res: dict) -> None:
    keys = ("n", "n_gated", "n_complement", "avg_R", "ctrl_avg_R", "observed_rate",
            "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
            "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "gate_rate")
    for k in keys:
        if res.get(k) is not None:
            print(f"  {k:15s} {res[k]}")
