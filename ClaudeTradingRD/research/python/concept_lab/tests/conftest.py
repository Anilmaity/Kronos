"""Shared fixtures: synthetic M1 markets with known truth, and isolation.

Tests never write to the real campaign cache or results directory.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="concept_lab_tests_")
os.environ.setdefault("CONCEPT_LAB_CACHE", str(Path(_TMP) / "cache"))
os.environ.setdefault("CONCEPT_LAB_RESULTS", str(Path(_TMP) / "results"))
os.environ["CONCEPT_LAB_LEDGER"] = str(Path(_TMP) / "ledger.jsonl")     # never the campaign's
os.environ.pop("CONCEPT_LAB_LEDGER_DISABLE", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))        # research/python

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402
import pytest               # noqa: E402

REAL_PARQUET = Path(__file__).resolve().parents[4] / "m3_scalper" / "xau_m1_full.parquet"
needs_real = pytest.mark.skipif(not REAL_PARQUET.exists(), reason="real XAUUSD parquet absent")


def make_m1(start="2016-01-04", end="2025-12-31", utc_hours=(13, 17), seed=0,
            vol=0.25, drift_at=None, drift_len=60, drift=0.0, price=1500.0,
            weekdays_only=True) -> pd.DataFrame:
    """Synthetic M1: a random walk trading `utc_hours` [a, b) each weekday.

    drift_at: optional (positions, signs) — adds `drift * sign` per bar to the
    increments of the `drift_len` bars STARTING at each position (i.e. strictly
    after an event whose decision is that bar's start). That is a planted edge
    of known size and known timing.
    """
    days = pd.date_range(start, end, freq="D", tz="UTC")
    if weekdays_only:
        days = days[days.dayofweek < 5]
    a, b = utc_hours
    per = (b - a) * 60
    offs = pd.to_timedelta(np.arange(per), unit="min") + pd.Timedelta(hours=a)
    idx = (days.repeat(per) + np.tile(offs, len(days))).as_unit("ns")
    rng = np.random.default_rng(seed)
    n = len(idx)
    inc = rng.normal(0, vol, n)
    if drift_at is not None:
        pos, sg = drift_at
        for p, s in zip(pos, sg):
            inc[p:p + drift_len] += drift * s
    close = price + np.cumsum(inc)
    op = np.concatenate([[price], close[:-1]])
    wig = np.abs(rng.normal(0, vol * 0.4, (2, n)))
    hi = np.maximum(op, close) + wig[0]
    lo = np.minimum(op, close) - wig[1]
    return pd.DataFrame({"open": op, "high": hi, "low": lo, "close": close},
                        index=pd.DatetimeIndex(idx, name="time"))


def event_positions(m1: pd.DataFrame, n: int, seed: int, minute: int = 0,
                    utc_hour: int = 14) -> np.ndarray:
    """Positions of n distinct M1 bars at hh:minute UTC (a bar-close grid)."""
    t = m1.index
    hours = np.atleast_1d(utc_hour)
    cand = np.flatnonzero(np.isin(t.hour, hours) & (t.minute == minute))
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(cand, size=min(n, len(cand)), replace=False))


def events_at(m1, pos, direction, stop_dist=2.0, rr=1.0):
    t = m1.index[pos]
    return pd.DataFrame({"decision_time": t, "available_at": t,
                         "direction": np.asarray(direction), "stop_dist": stop_dist,
                         "rr": rr})


@pytest.fixture(scope="session")
def flat_m1():
    return make_m1(seed=1)


@pytest.fixture
def tmp_results(tmp_path):
    return tmp_path / "results"
