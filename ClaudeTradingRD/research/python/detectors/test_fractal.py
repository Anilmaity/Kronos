"""Tests for the fractal model C2 / C3 detectors."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detectors.fractal import c2_events, c3_events  # noqa: E402


def mk(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1D", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


# ── C2 ────────────────────────────────────────────────────────────────────────
def test_bullish_c2_sweeps_low_and_closes_back_inside():
    df = mk([
        (100, 105, 95, 102),      # 0 reference candle: low 95
        (100, 103, 92, 101),      # 1 sweeps 95, closes 101 back inside, close>open
    ])
    ev = c2_events(df)
    assert len(ev) == 1
    r = ev.iloc[0]
    assert r["direction"] == "bullish"
    assert r["ref_level"] == 95.0


def test_bearish_c2_sweeps_high_and_closes_back_inside():
    df = mk([
        (100, 105, 95, 100),
        (102, 108, 99, 99.5),     # sweeps 105, closes back inside, close<open
    ])
    ev = c2_events(df)
    assert len(ev) == 1
    assert ev.iloc[0]["direction"] == "bearish"
    assert ev.iloc[0]["ref_level"] == 105.0


def test_close_outside_is_expansion_not_c2():
    df = mk([(100, 105, 95, 102), (100, 103, 92, 94)])   # closes below 95
    assert c2_events(df).empty


def test_require_close_inside_can_be_relaxed():
    """The corpus never says whether a body close outside disqualifies the sweep."""
    # sweeps 95, closes 94 (outside the ref low) but is genuinely an up-close bar
    df = mk([(100, 105, 95, 102), (92.5, 103, 92, 94)])
    assert c2_events(df, require_close_inside=True).empty
    assert not c2_events(df, require_close_inside=False).empty


def test_reversal_close_requirement_filters_wrong_direction_close():
    df = mk([(100, 105, 95, 102), (102, 103, 92, 97)])   # sweeps low but closes DOWN
    assert c2_events(df, require_reversal_close=True).empty
    assert not c2_events(df, require_reversal_close=False).empty


def test_lookback_extreme_reading_finds_pool_sweeps():
    """The other contested reading: sweep a nearby pool, not the prior candle."""
    df = mk([
        (100, 105, 90, 100),      # 0 pool low 90
        (100, 104, 96, 100),      # 1
        (100, 103, 95, 100),      # 2 prior candle low 95
        (99, 102, 89, 101),       # 3 sweeps 90 (pool) and 95 (prior)
    ])
    prior = c2_events(df, sweep_ref="prior_candle")
    pool = c2_events(df, sweep_ref="lookback_extreme", lookback=3)
    assert prior.iloc[-1]["ref_level"] == 95.0
    assert pool.iloc[-1]["ref_level"] == 90.0, "pool reading uses the deeper extreme"


def test_wick_ratio_and_half_wick_level():
    # range 92..103; body 100..101 -> lower wick = 100-92 = 8 of range 11
    df = mk([(100, 105, 95, 102), (100, 103, 92, 101)])
    r = c2_events(df).iloc[0]
    assert abs(r["wick_ratio"] - 8 / 11) < 1e-9
    assert r["half_wick_level"] == 96.0, "0.5 of the sweeping wick: 92 + (100-92)/2"


def test_max_body_ratio_filter():
    df = mk([(100, 105, 95, 102), (96, 103, 92, 102)])   # large body
    assert not c2_events(df, max_body_ratio=1.0).empty
    assert c2_events(df, max_body_ratio=0.05).empty


def test_bad_sweep_ref_rejected():
    with pytest.raises(ValueError):
        c2_events(mk([(1, 1, 1, 1)]), sweep_ref="vibes")


# ── C3 ────────────────────────────────────────────────────────────────────────
def seq_df():
    return mk([
        (100, 105, 95, 102),        # 0 reference
        (100, 103, 92, 101),        # 1 bullish C2 (open 100)
        (101, 110, 100.5, 109),     # 2 C3: closes 109 > C2 open 100, shallow wick
    ])


def test_sequential_c3_follows_c2():
    ev = c3_events(seq_df(), mode="sequential")
    assert len(ev) == 1
    r = ev.iloc[0]
    assert r["direction"] == "bullish"
    assert r["time"] == seq_df().index[2]
    assert r["c2_time"] == seq_df().index[1]
    assert bool(r["delivered_beyond_c2_open"]) is True


def test_sequential_c3_requires_close_beyond_c2_open_when_asked():
    df = mk([
        (100, 105, 95, 102),
        (100, 103, 92, 101),        # C2 open 100
        (101, 102, 99, 99.5),       # closes 99.5, NOT beyond 100
    ])
    assert c3_events(df, mode="sequential", require_close_beyond_c2_open=True).empty
    assert not c3_events(df, mode="sequential",
                         require_close_beyond_c2_open=False).empty


def test_wick_in_half_filter():
    df = mk([
        (100, 105, 95, 102),
        (100, 103, 92, 101),
        (101, 110, 90, 109),        # deep counter wick: 101-90 = 11 of range 20
    ])
    assert not c3_events(df, mode="sequential", require_wick_in_half=False).empty
    assert c3_events(df, mode="sequential", require_wick_in_half=True).empty


def test_standalone_mode_needs_no_c2():
    """The looser reading: no sweep required, EQ of the prior candle respected."""
    df = mk([
        (100, 110, 90, 100),        # prior mid = 100
        (100, 108, 99, 106),        # closes 106 > 100 -> bullish standalone C3
    ])
    seq = c3_events(df, mode="sequential")
    alone = c3_events(df, mode="standalone")
    assert seq.empty
    assert len(alone) == 1
    assert alone.iloc[0]["direction"] == "bullish"
    assert pd.isna(alone.iloc[0]["c2_time"])


def test_the_two_c3_modes_disagree():
    """If they agreed, `contested` on the concept would be wrong."""
    df = seq_df()
    seq = set(c3_events(df, mode="sequential")["time"])
    alone = set(c3_events(df, mode="standalone")["time"])
    assert seq != alone


def test_bad_mode_rejected():
    with pytest.raises(ValueError):
        c3_events(seq_df(), mode="freestyle")


def test_empty_inputs_are_safe():
    empty = pd.DataFrame(columns=["open", "high", "low", "close"])
    assert c2_events(empty).empty
    assert c3_events(empty).empty
    assert c3_events(empty, mode="standalone").empty


@pytest.mark.skipif(not (Path(__file__).resolve().parents[3] / "m3_scalper"
                         / "xau_m1_3y.parquet").exists(),
                    reason="XAUUSD parquet not available")
def test_real_data_c2_c3_are_plausible():
    from bars import load_m1, resample

    d1 = resample(load_m1(), "1D")
    c2 = c2_events(d1)
    assert 0 < len(c2) < len(d1), "C2 should be common but not universal"

    # The pool reading sweeps a wider net, so it cannot find fewer than the
    # prior-candle reading on the same data.
    pool = c2_events(d1, sweep_ref="lookback_extreme", lookback=5)
    assert len(pool) <= len(c2) * 3

    c3 = c3_events(d1, mode="sequential")
    assert len(c3) <= len(c2), "every sequential C3 needs a C2"
