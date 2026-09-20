"""Deterministic tests for the primitive detectors.

Hand-built bar series with a KNOWN answer, so a failure means the detector is
wrong rather than the market being unusual. Real-data smoke checks live at the
bottom and are skipped when the parquet is absent.

Run:  python -m pytest detectors/test_primitives.py -q      (from research/python)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detectors.primitives import (  # noqa: E402
    candle_range_sweep, displacement, fair_value_gaps, swing_points,
    sweep_of_level,
)


def mk(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """rows of (open, high, low, close) -> 1-minute OHLC frame."""
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1min", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


# ── swing points ──────────────────────────────────────────────────────────────
def test_swing_high_detected_at_the_peak():
    # highs: 1,2,3,2,1 -> a swing high at index 2 only
    df = mk([(0, 1, 0, 0), (0, 2, 0, 0), (0, 3, 0, 0), (0, 2, 0, 0), (0, 1, 0, 0)])
    sw = swing_points(df, left=2, right=2)
    assert list(sw["swing_high"]) == [False, False, True, False, False]


def test_swing_low_detected_at_the_trough():
    df = mk([(0, 0, 5, 0), (0, 0, 4, 0), (0, 0, 1, 0), (0, 0, 4, 0), (0, 0, 5, 0)])
    sw = swing_points(df, left=2, right=2)
    assert list(sw["swing_low"]) == [False, False, True, False, False]


def test_swing_confirmation_is_not_instant():
    """A swing is only knowable `right` bars later — guards against look-ahead."""
    df = mk([(0, 1, 0, 0), (0, 2, 0, 0), (0, 3, 0, 0), (0, 2, 0, 0), (0, 1, 0, 0)])
    sw = swing_points(df, left=2, right=2)
    peak = sw.index[2]
    assert sw.loc[peak, "confirmed_at"] == sw.index[4]
    assert sw.loc[peak, "confirmed_at"] > peak


def test_swing_rejects_bad_params():
    df = mk([(0, 1, 0, 0)] * 5)
    with pytest.raises(ValueError):
        swing_points(df, left=0, right=2)


# ── sweeps ────────────────────────────────────────────────────────────────────
def test_sweep_requires_close_back_inside():
    # bar 0 pierces 10 and closes back under; bar 1 pierces and closes above.
    df = mk([(9, 11, 9, 9.5), (9, 11, 9, 10.5)])
    s = sweep_of_level(df, 10.0, "buy_side")
    assert list(s) == [True, False], "a close beyond the level is expansion, not a sweep"


def test_sweep_without_close_back_flag_counts_both():
    df = mk([(9, 11, 9, 9.5), (9, 11, 9, 10.5)])
    s = sweep_of_level(df, 10.0, "buy_side", require_close_back=False)
    assert list(s) == [True, True]


def test_sell_side_sweep():
    df = mk([(11, 11, 9, 10.5), (11, 11, 9, 9.5)])
    s = sweep_of_level(df, 10.0, "sell_side")
    assert list(s) == [True, False]


def test_sweep_rejects_bad_side():
    with pytest.raises(ValueError):
        sweep_of_level(mk([(1, 1, 1, 1)]), 1.0, "sideways")


# ── candle range theory ───────────────────────────────────────────────────────
def test_c2_sweeps_c1_high_then_closes_inside():
    c1 = (10, 12, 8, 11)
    c2 = (11, 13, 10, 11.5)          # takes C1 high, closes back inside
    out = candle_range_sweep(mk([c1, c2]))
    assert bool(out["swept_high"].iloc[1]) is True
    assert bool(out["expansion_up"].iloc[1]) is False
    assert out["c1_mid"].iloc[1] == 10.0


def test_c2_closing_beyond_is_expansion_not_sweep():
    out = candle_range_sweep(mk([(10, 12, 8, 11), (11, 14, 10, 13)]))
    assert bool(out["swept_high"].iloc[1]) is False
    assert bool(out["expansion_up"].iloc[1]) is True


def test_c2_taking_both_sides():
    out = candle_range_sweep(mk([(10, 12, 8, 11), (11, 13, 7, 10)]))
    assert bool(out["swept_both"].iloc[1]) is True


def test_inside_bar_flagged_and_no_sweep():
    out = candle_range_sweep(mk([(10, 12, 8, 11), (10, 11, 9, 10)]))
    assert bool(out["inside_bar"].iloc[1]) is True
    assert bool(out["swept_high"].iloc[1]) is False
    assert bool(out["swept_low"].iloc[1]) is False


def test_first_bar_has_no_c1_and_never_fires():
    out = candle_range_sweep(mk([(10, 12, 8, 11), (11, 13, 10, 11.5)]))
    assert bool(out["swept_high"].iloc[0]) is False
    assert pd.isna(out["c1_high"].iloc[0])


# ── fair value gaps ───────────────────────────────────────────────────────────
def test_bullish_fvg():
    # bar2.low (12) > bar0.high (10) -> bullish gap 10..12
    df = mk([(9, 10, 9, 10), (10, 13, 10, 12), (12, 14, 12, 13)])
    g = fair_value_gaps(df)
    assert bool(g["bullish_fvg"].iloc[2]) is True
    assert (g["gap_low"].iloc[2], g["gap_high"].iloc[2]) == (10.0, 12.0)
    assert g["gap_size"].iloc[2] == 2.0


def test_bearish_fvg():
    df = mk([(14, 15, 14, 14), (12, 13, 10, 11), (10, 11, 9, 10)])
    g = fair_value_gaps(df)
    assert bool(g["bearish_fvg"].iloc[2]) is True
    assert (g["gap_low"].iloc[2], g["gap_high"].iloc[2]) == (11.0, 14.0)


def test_no_fvg_when_ranges_overlap():
    df = mk([(9, 12, 9, 11), (10, 13, 10, 12), (11, 14, 11, 13)])
    g = fair_value_gaps(df)
    assert not g["bullish_fvg"].any()
    assert not g["bearish_fvg"].any()


# ── displacement ──────────────────────────────────────────────────────────────
def test_displacement_uses_trailing_window_excluding_itself():
    rows = [(0, 1, 0, 1)] * 20 + [(0, 10, 0, 10)]   # 20 unit bodies, then a 10x
    d = displacement(mk(rows), lookback=20, mult=2.0)
    assert bool(d.iloc[20]) is True
    assert not d.iloc[:20].any(), "warm-up window must not fire"


def test_displacement_quiet_series_never_fires():
    d = displacement(mk([(0, 1, 0, 1)] * 40), lookback=20, mult=2.0)
    assert not d.any()


# ── real-data smoke ───────────────────────────────────────────────────────────
@pytest.mark.skipif(not (Path(__file__).resolve().parents[3] / "m3_scalper"
                         / "xau_m1_3y.parquet").exists(),
                    reason="XAUUSD parquet not available")
def test_real_data_sanity():
    """Sanity, not correctness: the primitives must produce plausible rates on
    3 years of real XAUUSD rather than firing on every bar or never firing."""
    from bars import load_m1, resample

    d1 = resample(load_m1(), "1D")
    assert len(d1) > 500

    crt = candle_range_sweep(d1)
    swept = int((crt["swept_high"] | crt["swept_low"]).sum())
    assert 0 < swept < len(d1), "sweeps should be common but not universal"

    sw = swing_points(d1, 2, 2)
    n_sw = int(sw["swing_high"].sum() + sw["swing_low"].sum())
    assert 0 < n_sw < len(d1) * 0.8

    g = fair_value_gaps(d1)
    assert int(g["bullish_fvg"].sum() + g["bearish_fvg"].sum()) > 0

    assert 0 < int(displacement(d1).sum()) < len(d1) * 0.5
