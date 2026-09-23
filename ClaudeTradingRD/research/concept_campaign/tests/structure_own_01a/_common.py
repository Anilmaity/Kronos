"""Shared, pure detector pieces for batch structure_own_01a (TTrades own-voice structure).

Everything is a pure function of the M1 frame it is given (bars built with
cl.build_bars from the INPUT), so probe_lookahead can re-run it on truncated slices.

Conventions fixed for the whole batch BEFORE any test was run:
  * daily candle = NY trading day rolling at 18:00 (method_spec §1.4, canon [P]); sessions
    with < 600 M1 bars are stub sessions (README trap 6) and are dropped before any
    previous-candle comparison;
  * previous-candle engine (method_spec §2.3): a CONTINUATION (expansion) closure takes out
    the previous candle's high (low) AND closes beyond it;
  * 1h CISD = the locked phase-3 configuration (conjunction_preregistration §1.8):
    swing 2/2, level_rule series_open, max_wait 3, stop at the protected swing, 2R.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events      # noqa: E402

OHLC = ["open", "high", "low", "close"]
STUB_MIN_M1 = 600


def daily(m1: pd.DataFrame) -> pd.DataFrame:
    """18:00-NY daily bars built from m1, stub sessions dropped."""
    d = cl.build_bars(m1, "1D")
    return d[d["n_m1"] >= STUB_MIN_M1].copy()


def continuation_flags(b: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(up, down) continuation closures vs the previous row of b."""
    H, L, C = (b[c].to_numpy(float) for c in ("high", "low", "close"))
    ph, pl = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    up = (H > ph) & (C > ph)
    dn = (L < pl) & (C < pl)
    return up, dn


def cisd_1h(m1: pd.DataFrame):
    """Locked phase-3 1h CISD events on 1h bars built from m1.

    Returns (bars, ev) where ev carries decision/stop columns plus the level, the
    confirming bar's start time and its positional index.
    """
    b = cl.build_bars(m1, "1h")
    cols = ["direction", "level", "protected_swing", "confirm_time", "conf_pos", "decision_time"]
    if len(b) < 10:
        return b, pd.DataFrame(columns=cols)
    ev = cisd_events(b[OHLC], level_rule="series_open", left=2, right=2, max_wait=3,
                     min_series=1)
    if ev.empty:
        return b, pd.DataFrame(columns=cols)
    ev = ev.copy()
    ev["conf_pos"] = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    ev["decision_time"] = pd.DatetimeIndex(b["close_time"].to_numpy()[ev["conf_pos"].to_numpy()])
    return b, ev.reset_index(drop=True)


def show(res: dict) -> None:
    for k in ("test_type", "n", "n_gated", "n_complement", "dropped", "avg_R", "win_rate",
              "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "ci_method", "p", "mde",
              "verdict", "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "gate_rate",
              "dependence", "halves"):
        if k in res:
            print(f"  {k}: {res.get(k)}")
