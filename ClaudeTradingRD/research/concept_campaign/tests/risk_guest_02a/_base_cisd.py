"""Shared base book for the trade-management concepts of batch risk_guest_02a.

Base entry model (the management concepts say "as per the entry model"): the
harness's canonical phase-3 book — 1h bare CISD, series_open level, 2/2 swings,
max_wait=3, decide at the confirming 1h bar's close, enter at the next M1 open,
stop at the protected swing, hold at most 10h (phase-3 §1.8-1.13 locked config).

T1 (first target) := the nearest confirmed, still-unbroken 1h 2/2 swing high above
the entry price (long; mirrored for a short), searched over the last 200 1h bars.
This is the t1-t2-partial-system corpus definition ("T1 := the nearest prior swing
low (for a short: high) that the model's structure targets").

Everything here is pure in its M1 input so probe_lookahead can re-run it on slices.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

BASE_HOLD = pd.Timedelta("10h")
T1_LOOKBACK_BARS = 200
MIN_T1_R = 0.25          # T1 must sit >= 0.25 x initial risk from entry (declared)
ONE_MIN = np.timedelta64(60_000_000_000, "ns")


def _ns(idx) -> np.ndarray:
    return pd.DatetimeIndex(idx).tz_convert("UTC").as_unit("ns").asi8


def base_book(m1: pd.DataFrame) -> pd.DataFrame:
    """One row per 1h CISD trade: decision, entry index/price, stop, T1, hold end."""
    b = cl.build_bars(m1, "1h")
    ohlc = b[["open", "high", "low", "close"]]
    ev = cisd_events(ohlc, level_rule="series_open", left=2, right=2, max_wait=3,
                     min_series=1)
    cols = ["dec_ns", "dir", "i0", "entry", "stop", "t1", "hold_end_ns"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close_ns = _ns(b["close_time"])
    bpos = pd.Index(b.index)
    conf_pos = bpos.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    dec_ns = close_ns[conf_pos]
    dirs = np.where(ev["direction"].to_numpy() == "bullish", 1, -1)
    stop = ev["protected_swing"].to_numpy(float)

    sw = swing_points(ohlc, left=2, right=2)
    is_h = sw["swing_high"].to_numpy()
    is_l = sw["swing_low"].to_numpy()
    n = len(b)
    conf_ns = np.full(n, np.iinfo(np.int64).max, dtype=np.int64)
    conf_ns[: max(0, n - 2)] = close_ns[2:]          # swing at i known at close of i+2
    H = b["high"].to_numpy(float)
    L = b["low"].to_numpy(float)

    mt = _ns(m1.index)
    mo = m1["open"].to_numpy(float)
    i0 = np.searchsorted(mt, dec_ns, side="left")
    ok = i0 < len(mt)
    entry = np.full(len(ev), np.nan)
    entry[ok] = mo[i0[ok]]

    t1 = np.full(len(ev), np.nan)
    for r in range(len(ev)):
        if not ok[r]:
            continue
        j = conf_pos[r]                               # last 1h bar closed at decision
        lo = max(0, j - T1_LOOKBACK_BARS)
        E = entry[r]
        best = np.nan
        if dirs[r] == 1:
            cand = np.nonzero(is_h[lo:j + 1])[0] + lo
            for i in cand:
                if conf_ns[i] > dec_ns[r] or H[i] <= E:
                    continue
                if i + 1 <= j and H[i + 1:j + 1].max() > H[i]:
                    continue                          # already run: no liquidity left
                if np.isnan(best) or H[i] < best:
                    best = H[i]
        else:
            cand = np.nonzero(is_l[lo:j + 1])[0] + lo
            for i in cand:
                if conf_ns[i] > dec_ns[r] or L[i] >= E:
                    continue
                if i + 1 <= j and L[i + 1:j + 1].min() < L[i]:
                    continue
                if np.isnan(best) or L[i] > best:
                    best = L[i]
        t1[r] = best
    out = pd.DataFrame({"dec_ns": dec_ns, "dir": dirs, "i0": i0, "entry": entry,
                        "stop": stop, "t1": t1,
                        "hold_end_ns": dec_ns + BASE_HOLD.value})
    valid = ok & np.isfinite(t1) & np.isfinite(stop) & \
        (((dirs == 1) & (stop < entry)) | ((dirs == -1) & (stop > entry)))
    with np.errstate(invalid="ignore", divide="ignore"):
        valid &= np.abs(t1 - entry) >= MIN_T1_R * np.abs(entry - stop)
    return out[valid].reset_index(drop=True)


def first_stop_or_t1(m1: pd.DataFrame, bk: pd.DataFrame) -> pd.DataFrame:
    """For each base trade: M1 index of the first stop or T1 touch within the hold
    (stop wins a same-bar tie, as in the harness). kind: 1 = T1, -1 = stop, 0 = none."""
    mt = _ns(m1.index)
    mh = m1["high"].to_numpy(float)
    ml = m1["low"].to_numpy(float)
    kk = np.full(len(bk), -1, dtype=np.int64)
    kind = np.zeros(len(bk), dtype=np.int64)
    for r, row in enumerate(bk.itertuples(index=False)):
        a = int(row.i0)
        e = int(np.searchsorted(mt, row.hold_end_ns, side="left"))
        if e <= a:
            continue
        if row.dir == 1:
            s_hit = ml[a:e] <= row.stop
            t_hit = mh[a:e] >= row.t1
        else:
            s_hit = mh[a:e] >= row.stop
            t_hit = ml[a:e] <= row.t1
        any_hit = s_hit | t_hit
        if not any_hit.any():
            continue
        k = int(np.argmax(any_hit))
        kk[r] = a + k
        kind[r] = -1 if s_hit[k] else 1
    return pd.DataFrame({"k": kk, "kind": kind})
