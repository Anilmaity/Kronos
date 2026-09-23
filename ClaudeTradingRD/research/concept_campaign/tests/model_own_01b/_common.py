"""Shared helpers for batch model_own_01b (pure functions of the M1 input).

Every helper builds its bars FROM the M1 frame it is given, so detectors that use
them stay probe-able by cl.probe_lookahead.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

PHASE3 = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked config)"
BATCH_DIR = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b"


def cisd_book(m1: pd.DataFrame, tf: str, grid4h: str = "forex") -> pd.DataFrame:
    """Phase-3 bare CISD book on `tf`: series_open, swing 2/2, max_wait 3,
    decide at the confirming bar's close, stop at the protected swing, 2R.
    Extra columns: extreme_time (bar START of the swept extreme), extreme_price."""
    b = cl.build_bars(m1, tf, grid4h=grid4h)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "extreme_time", "extreme_price"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close,
        "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "rr": 2.0,
        "extreme_time": pd.DatetimeIndex(ev["extreme_time"]),
        "extreme_price": ev["extreme_price"].to_numpy(float),
    })
    return out.sort_values("decision_time").reset_index(drop=True)


def developing_day(m1: pd.DataFrame, times) -> pd.DataFrame:
    """State of the CURRENT (18:00 NY) daily candle from M1 bars closed by t:
    open (first M1 open of t's trading day), running high/low, and the close of
    the last M1 bar closed by t. NaN when no bar of t's day has closed."""
    tt = pd.DatetimeIndex(times).tz_convert("UTC")
    idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
    td = cl.trading_day(idx)
    first_open = pd.Series(m1["open"].to_numpy(), index=td).groupby(level=0).first()
    closes_at = idx + pd.Timedelta(minutes=1)
    pos = np.searchsorted(cl.data.utc_ns(closes_at), cl.data.utc_ns(tt), side="right") - 1
    ok = pos >= 0
    p = np.clip(pos, 0, None)
    last_close = m1["close"].to_numpy()[p]
    last_td = td[p]
    t_td = cl.trading_day(tt)
    same = ok & np.asarray(last_td == t_td)
    rh = cl.running_hilo(tt, "1D", m1=m1)
    op = first_open.reindex(t_td).to_numpy()
    out = pd.DataFrame({"d_open": np.where(same, op, np.nan),
                        "d_high": np.where(same, rh["high"].to_numpy(), np.nan),
                        "d_low": np.where(same, rh["low"].to_numpy(), np.nan),
                        "d_close": np.where(same, last_close, np.nan)}, index=tt)
    return out


def prev_candle_state(b: pd.DataFrame) -> pd.DataFrame:
    """§2.3 previous-candle engine on a closed-bar frame (row i vs row i-1).
    state: continuation / reversal / both / inside; implied = bias for NEXT candle
    (+1/-1/0). No inside-bar trend default (declared: inside -> 0)."""
    h, l, c = b["high"], b["low"], b["close"]
    ph, pl = h.shift(1), l.shift(1)
    th = (h > ph).fillna(False).to_numpy()
    tl = (l < pl).fillna(False).to_numpy()
    ca = (c > ph).fillna(False).to_numpy()
    cb = (c < pl).fillna(False).to_numpy()
    state = np.full(len(b), "inside", dtype=object)
    imp = np.zeros(len(b), int)
    oh, ol = th & ~tl, tl & ~th
    state[th & tl] = "both"
    state[oh & ca] = "continuation"; imp[oh & ca] = 1
    state[oh & ~ca] = "reversal"; imp[oh & ~ca] = -1
    state[ol & cb] = "continuation"; imp[ol & cb] = -1
    state[ol & ~cb] = "reversal"; imp[ol & ~cb] = 1
    return pd.DataFrame({"state": state, "implied": imp, "prev_high": ph.to_numpy(),
                         "prev_low": pl.to_numpy()}, index=b.index)


def summary(res: dict) -> str:
    keys = ("n", "n_gated", "avg_R", "observed_rate", "null_rate", "diff", "ci_lo",
            "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars",
            "gate_rate", "ctrl_overlap")
    return "\n".join(f"  {k:15s} {res[k]}" for k in keys if res.get(k) is not None)
