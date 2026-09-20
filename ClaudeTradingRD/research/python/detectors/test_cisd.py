"""Tests for the CISD detector.

Hand-built series where the correct answer is known by construction, so a failure
implicates the detector rather than the market. The contested `level_rule`
readings are tested separately, since the whole point is that they disagree.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detectors.cisd import LEVEL_RULES, cisd_events, compare_level_rules  # noqa: E402


def mk(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def bull_case():
    """Three down-close candles into a low, then a rally closing back through.

    Run = bars 2,3,4 (each close < open). Bar 4 is the swing low at 90.
      series_close   = close of bar 4  =  91  -> crossed at bar 7
      series_open    = open  of bar 2  = 100  -> crossed at bar 8
      series_extreme = high of bars 2..4 = 101 -> crossed at bar 9

    Bars 5-6 deliberately stay below every level: with right=2 the swing low is
    not confirmable until bar 6, so no legal confirmation can occur before bar 7.
    Crossing the levels earlier would only test look-ahead behaviour.
    """
    return mk([
        (104, 105, 103, 104),        # 0
        (104, 105, 103, 104),        # 1
        (100, 101, 96, 97),          # 2  run start (down close)
        (97, 98, 93, 94),            # 3  down close
        (94, 95, 90, 91),            # 4  down close -> swing low at 90
        (91, 91.6, 90.5, 90.9),      # 5  below series_close
        (90.9, 91.4, 90.6, 90.95),   # 6  below series_close
        (90.95, 92, 90.8, 91.5),     # 7  closes > 91   (series_close)
        (91.5, 101, 91.4, 100.5),    # 8  closes > 100  (series_open)
        (100.5, 102, 100.3, 101.5),  # 9  closes > 101  (series_extreme)
        (101.5, 102, 101, 101.8),    # 10
        (101.8, 102, 101, 101.9),    # 11
    ])


def test_bullish_cisd_series_open():
    ev = cisd_events(bull_case(), level_rule="series_open", left=2, right=2)
    bull = ev[ev["direction"] == "bullish"]
    assert len(bull) == 1
    r = bull.iloc[0]
    assert r["level"] == 100.0
    assert r["series_len"] == 3
    assert r["extreme_price"] == 90.0
    assert r["confirm_time"] == bull_case().index[8]


def test_bullish_cisd_series_extreme_is_stricter():
    ev = cisd_events(bull_case(), level_rule="series_extreme", left=2, right=2)
    r = ev[ev["direction"] == "bullish"].iloc[0]
    assert r["level"] == 101.0
    assert r["confirm_time"] == bull_case().index[9], "stricter level confirms later"


def test_bullish_cisd_series_close_is_loosest():
    ev = cisd_events(bull_case(), level_rule="series_close", left=2, right=2)
    r = ev[ev["direction"] == "bullish"].iloc[0]
    assert r["level"] == 91.0
    assert r["confirm_time"] == bull_case().index[7], "loosest level confirms earliest"


def test_the_three_readings_actually_disagree():
    """If they agreed, `contested` in the concept file would be wrong."""
    times = {rule: cisd_events(bull_case(), level_rule=rule, left=2, right=2)
             .iloc[0]["confirm_time"] for rule in LEVEL_RULES}
    assert len(set(times.values())) == 3


def test_protected_swing_equals_the_extreme():
    r = cisd_events(bull_case(), level_rule="series_open").iloc[0]
    assert r["protected_swing"] == r["extreme_price"]


def test_no_event_when_price_never_closes_back_through():
    df = mk([
        (104, 105, 103, 104), (104, 105, 103, 104),
        (100, 101, 96, 97), (97, 98, 93, 94), (94, 95, 90, 91),
        (91, 92, 89.5, 90.5), (90.5, 91, 89, 90), (90, 91, 89, 90.2),
        (90.2, 91, 89, 90.1), (90.1, 91, 89, 90.3),
    ])
    ev = cisd_events(df, level_rule="series_open")
    assert ev[ev["direction"] == "bullish"].empty


def test_confirm_is_never_before_the_series_ends():
    ev = cisd_events(bull_case(), level_rule="series_close")
    for _, r in ev.iterrows():
        assert r["confirm_time"] > r["series_end"], "look-ahead: confirmed too early"
        assert r["bars_waited"] >= 1


def test_max_wait_suppresses_stale_confirmations():
    rows = [(104, 105, 103, 104), (104, 105, 103, 104),
            (100, 101, 96, 97), (97, 98, 93, 94), (94, 95, 90, 91)]
    rows += [(91, 92, 90, 91)] * 30            # long drift, no close through 100
    rows += [(91, 101, 90, 100.5)]             # closes through, but far too late
    df = mk(rows)
    assert cisd_events(df, level_rule="series_open", max_wait=5).empty
    assert not cisd_events(df, level_rule="series_open", max_wait=60).empty


def test_min_series_filters_single_candle_runs():
    """The corpus insists CISD comes from a series, never a single candle."""
    df = mk([
        (104, 105, 103, 104), (104, 105, 103, 104),
        (104, 105, 99, 100),                      # single down-close candle -> low
        (100, 106, 99.5, 105),                    # closes back through
        (105, 106, 104, 105), (105, 106, 104, 105),
        (105, 106, 104, 105), (105, 106, 104, 105),
    ])
    assert not cisd_events(df, min_series=1).empty
    assert cisd_events(df, min_series=2).empty


def test_bad_level_rule_rejected():
    with pytest.raises(ValueError):
        cisd_events(bull_case(), level_rule="whatever")


def test_empty_input_returns_empty_frame():
    empty = pd.DataFrame(columns=["open", "high", "low", "close"])
    assert cisd_events(empty).empty


@pytest.mark.skipif(not (Path(__file__).resolve().parents[3] / "m3_scalper"
                         / "xau_m1_3y.parquet").exists(),
                    reason="XAUUSD parquet not available")
def test_real_data_rule_comparison():
    """On real data the three readings must all fire, and the strict reading must
    not fire MORE often than the loose one."""
    from bars import load_m1, resample

    h1 = resample(load_m1(), "1h")
    cmp = compare_level_rules(h1, max_wait=40).set_index("level_rule")
    assert (cmp["events"] > 0).all()
    assert cmp.loc["series_extreme", "events"] <= cmp.loc["series_close", "events"]
