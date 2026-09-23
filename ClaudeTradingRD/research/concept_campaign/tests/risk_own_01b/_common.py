"""Shared pieces for batch risk_own_01b (my own code; the harness is untouched).

The baseline book used by every gate/variant in this batch is the campaign's
canonical rung-0 CISD book (concept_lab README example 2 / phase-3 locked config):
series_open level, 2/2 swings, max_wait 3, min_series 1, stop at the protected
swing, 2R target, decide at the confirming bar's close, enter the next M1 open.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

PY = "/Users/anil/Projects/Kronos/ClaudeTradingRD/.venv/bin/python"

BASE_PARAMS = {"level_rule": "series_open", "swing": "2/2", "max_wait": 3,
               "min_series": 1, "rr": 2.0}
BASE_SRC = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked rung-0 config)"
HOLD = {"15min": "150min", "30min": "300min", "1h": "10h", "4h": "40h", "1D": "10D"}
HOLD_SRC = "phase3: 10 entry-TF bars (§1.13), as in the concept_lab README examples"


def cisd_book(m1: pd.DataFrame, tf: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (events, raw cisd rows, bars). events has the harness columns plus
    positional helpers (conf_pos, ext_pos, s_pos, e_pos) into `bars`."""
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return pd.DataFrame(columns=cols), ev, b
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close,
        "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "rr": 2.0,
    })
    idx = b.index
    out["conf_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    out["ext_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    out["s_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["series_start"]))
    out["e_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["series_end"]))
    out["confirm_close"] = ev["confirm_close"].to_numpy(float)
    return out, ev, b


def m1_arrays(m1: pd.DataFrame):
    tn = cl.data.utc_ns(m1.index).astype(np.int64)
    return (tn, m1["open"].to_numpy(float), m1["high"].to_numpy(float),
            m1["low"].to_numpy(float), m1["close"].to_numpy(float))


def daily_ref(m1: pd.DataFrame, lookback: int = 20, min_n_m1: int = 600,
              opp_cut: float = 1.0) -> pd.DataFrame:
    """Per completed trading day (18:00 NY roll): its range and, as of its close,
    ADR = mean H-L of the last `lookback` real days (n_m1 >= min_n_m1, stub days
    skipped) INCLUDING it, and EXP = median H-L of the expansion days among them
    (opposing_run / |body| <= opp_cut; opposing run = open->extreme against the
    close direction). available_at = that day's close_time."""
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= min_n_m1].copy()
    rng = (d["high"] - d["low"]).to_numpy(float)
    o, c, h, l_ = (d[k].to_numpy(float) for k in ("open", "close", "high", "low"))
    body = np.abs(c - o)
    opp = np.where(c >= o, o - l_, h - o)
    with np.errstate(divide="ignore", invalid="ignore"):
        is_exp = (body > 0) & (opp / np.where(body > 0, body, np.nan) <= opp_cut)
    s_rng = pd.Series(rng)
    adr = s_rng.rolling(lookback, min_periods=lookback).mean().to_numpy()
    exp_r = pd.Series(np.where(is_exp, rng, np.nan))
    exp_med = exp_r.rolling(lookback, min_periods=1).median().to_numpy()
    n_exp = pd.Series(is_exp.astype(float)).rolling(lookback, min_periods=lookback).sum().to_numpy()
    exp_med = np.where(np.isfinite(adr) & (n_exp >= 3), exp_med, np.nan)
    return pd.DataFrame({"close_time": d["close_time"].to_numpy(), "range": rng,
                         "adr": adr, "exp_band": exp_med, "n_m1": d["n_m1"].to_numpy()},
                        index=d.index)


def asof_ref(ref: pd.DataFrame, times) -> pd.DataFrame:
    """Latest daily_ref row whose close_time <= t (the in-progress day is never read)."""
    ct = cl.data.utc_ns(pd.DatetimeIndex(ref["close_time"]))
    tn = cl.data.utc_ns(pd.DatetimeIndex(times))
    pos = np.searchsorted(ct, tn, side="right") - 1
    ok = pos >= 0
    r = ref.iloc[np.clip(pos, 0, None)].reset_index(drop=True)
    r.loc[~ok, :] = np.nan
    return r


def show(res: dict) -> None:
    keys = ("test_type", "claim", "n", "n_gated", "n_complement", "avg_R", "observed_rate",
            "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
            "ctrl_overlap", "ties", "exposure_bars", "gate_rate", "halves")
    for k in keys:
        if res.get(k) is not None:
            print(f"  {k:15s} {res[k]}")
