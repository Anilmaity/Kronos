"""Shared baseline for batch risk_own_01a (risk, TTrades own voice).

The baseline book every management/risk rule in this batch is applied to is the
phase-3 locked rung-0 CISD book (meta/conjunction_preregistration.md §1.8-1.13):
CISD, series_open level reading, 2/2 swings, max_wait=3, min_series=1; decide at
the confirming bar's close; stop at the protected swing; 2R; hold 10 entry-TF bars.

Everything here is PURE in its M1 input (bars are built from the slice passed in),
so probe_lookahead can re-run any detector built on it.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from concept_lab.data import utc_ns  # noqa: E402

CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
PHASE3_SRC = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked rung-0 config)"


def cisd_raw(m1: pd.DataFrame, tf: str = "1h"):
    """(bars, events-with-extra-columns). Extra columns are what the risk rules read."""
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], **CISD_KW)
    if ev.empty:
        return b, None
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    sgn = np.where(ev["direction"] == "bullish", 1, -1)
    o = b["open"].to_numpy(float)
    c = b["close"].to_numpy(float)
    pos = pd.Index(b.index)
    s = pos.get_indexer(pd.DatetimeIndex(ev["series_start"]))
    e = pos.get_indexer(pd.DatetimeIndex(ev["series_end"]))
    body = np.empty(len(ev))
    for k in range(len(ev)):          # phase-3 body_extreme_stops (§1.11 secondary stop)
        lo = np.minimum(o[s[k]:e[k] + 1], c[s[k]:e[k] + 1])
        hi = np.maximum(o[s[k]:e[k] + 1], c[s[k]:e[k] + 1])
        body[k] = lo.min() if sgn[k] > 0 else hi.max()
    out = pd.DataFrame({
        "decision_time": close,
        "available_at": close,
        "direction": sgn,
        "stop_px": ev["protected_swing"].to_numpy(float),
        "close_px": ev["confirm_close"].to_numpy(float),
        "level_px": ev["level"].to_numpy(float),
        "body_px": body,
    })
    return b, out.sort_values("decision_time", kind="stable").reset_index(drop=True)


def first_open_at_or_after(m1: pd.DataFrame, times) -> tuple[np.ndarray, np.ndarray]:
    """(position, open) of the first M1 bar starting at/after each time (harness entry)."""
    tn = utc_ns(m1.index)
    q = utc_ns(pd.DatetimeIndex(times))
    p = np.searchsorted(tn, q, side="left")
    ok = p < len(tn)
    px = np.full(len(p), np.nan)
    px[ok] = m1["open"].to_numpy(float)[p[ok]]
    return p, px
