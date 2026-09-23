"""Shared helpers for batch structure_own_03b (TTrades own-voice structure concepts).

* cisd_book(m1, tf): the phase-3 rung-0 CISD book (series_open, swing 2/2, max_wait 3,
  stop = protected swing, 2R) — the baseline book for the location/filter concepts.
* pair_h1(m1): gold H1 (built from the given M1) inner-joined with OANDA XAG_USD H1
  (m3_scalper/xag_h1_full.parquet, the correlate phase 3 used). A copy of the approach in
  liquidity_guest_01a/_smt_common.py (not imported: other batches' files are off limits).
  The correlate is cut at gold's last bar + 1h, so a probe that truncates M1 truncates it too.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

RD = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD")
H1 = pd.Timedelta(hours=1)
_RAW: dict = {}


def cisd_book(m1: pd.DataFrame, tf: str = "15min", rr: float = 2.0):
    """Rung-0 CISD events on `tf` bars built from m1. Returns (events, bars)."""
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "px", "bar_pos"]
    if ev.empty:
        return pd.DataFrame(columns=cols), b
    pos = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[pos])
    out = pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float), "rr": rr,
        "px": ev["confirm_close"].to_numpy(float), "bar_pos": pos,
    })
    out = out.drop_duplicates(subset=["decision_time", "direction"])
    return out.sort_values("decision_time").reset_index(drop=True), b


def _raw_xag() -> pd.DataFrame:
    if "xag" not in _RAW:
        x = pd.read_parquet(RD / "m3_scalper" / "xag_h1_full.parquet")
        if "time" in x.columns:
            x = x.set_index("time")
        x.index = pd.to_datetime(x.index, utc=True)
        _RAW["xag"] = x[["open", "high", "low", "close"]].astype("float64").sort_index()
    return _RAW["xag"]


def pair_h1(m1: pd.DataFrame) -> pd.DataFrame:
    """g_* gold, s_* silver on joined H1 labels, plus close_time (gold's)."""
    cutoff = m1.index[-1] + H1
    g = cl.build_bars(m1, "1h")[["open", "high", "low", "close", "close_time"]]
    s = _raw_xag()
    s = s[s.index + H1 <= cutoff]
    idx = g.index.intersection(s.index)
    G, S = g.loc[idx], s.loc[idx]
    return pd.DataFrame({"g_open": G.open, "g_high": G.high, "g_low": G.low,
                         "g_close": G.close, "s_open": S.open, "s_high": S.high,
                         "s_low": S.low, "s_close": S.close,
                         "close_time": G.close_time}, index=idx)


def swing_range(b: pd.DataFrame, times, left: int = 2, right: int = 2) -> pd.DataFrame:
    """Latest confirmed fractal swing high/low on bars `b` at each time, re-anchored.

    A swing at bar i is known once bar i+right has CLOSED. range_high = the max high of
    the closed bars from the latest confirmed swing high through the last bar closed by t
    (the range expands while a new extreme forms, per premium-discount-equilibrium);
    range_low mirrored. Returns range_high, range_low, avail (the last closed bar's
    close_time), NaN where either swing is missing.
    """
    from detectors.primitives import swing_points
    sw = swing_points(b[["high", "low"]], left, right)
    ct = cl.data.utc_ns(pd.DatetimeIndex(b["close_time"]))
    h, lo = b["high"].to_numpy(float), b["low"].to_numpy(float)
    n = len(b)
    ih = np.flatnonzero(sw["swing_high"].to_numpy())
    il = np.flatnonzero(sw["swing_low"].to_numpy())
    ih, il = ih[ih + right < n], il[il + right < n]
    ch, cl_ = ct[ih + right], ct[il + right]
    tn = cl.data.utc_ns(pd.DatetimeIndex(times))
    k = np.searchsorted(ct, tn, side="right") - 1            # last closed bar
    jh = np.searchsorted(ch, tn, side="right") - 1
    jl = np.searchsorted(cl_, tn, side="right") - 1
    out_h = np.full(len(tn), np.nan)
    out_l = np.full(len(tn), np.nan)
    av = np.full(len(tn), np.datetime64("NaT"), dtype="datetime64[ns]")
    for r in range(len(tn)):
        if k[r] < 0 or jh[r] < 0 or jl[r] < 0:
            continue
        a, c = ih[jh[r]], il[jl[r]]
        out_h[r] = h[a:k[r] + 1].max()
        out_l[r] = lo[c:k[r] + 1].min()
        av[r] = ct[k[r]]
    return pd.DataFrame({"range_high": out_h, "range_low": out_l,
                         "avail": pd.DatetimeIndex(av).tz_localize("UTC")})


def show(res: dict) -> None:
    keys = ("n", "n_gated", "n_complement", "fire_rate", "avg_R", "diff", "ci_lo", "ci_hi",
            "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties", "ctrl_overlap",
            "observed_rate", "null_rate", "halves")
    for k in keys:
        if k in res and res[k] is not None:
            print(f"  {k:14s} {res[k]}")
