"""Tests for order blocks and protected swings."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detectors.blocks import (  # noqa: E402
    block_still_valid, first_mitigation, order_blocks, protected_swing_chain,
)


def mk(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def bull_then_retest():
    """Down-close run into a low, CISD close above, then a pullback into the zone.

    Run = bars 2,3,4.  bodies span 91..100 ; wicks span 90..101
    """
    return mk([
        (104, 105, 103, 104),        # 0
        (104, 105, 103, 104),        # 1
        (100, 101, 96, 97),          # 2 run start
        (97, 98, 93, 94),            # 3
        (94, 95, 90, 91),            # 4 swing low 90
        (91, 91.6, 90.5, 90.9),      # 5
        (90.9, 91.4, 90.6, 90.95),   # 6
        (91, 101.5, 90.9, 101.2),    # 7 CISD: closes above 101 (extreme) and 100
        (101.2, 102, 99, 99.5),      # 8 pulls back into the body zone
        (99.5, 100, 95, 96),         # 9 deeper, below the 95.5 midpoint
        (96, 103, 95, 102),          # 10
        (102, 103, 101, 102),        # 11
    ])


def test_order_block_body_zone():
    b = order_blocks(bull_then_retest(), zone="body", level_rule="series_extreme")
    bull = b[b["direction"] == "bullish"]
    assert len(bull) == 1
    r = bull.iloc[0]
    assert r["zone_low"] == 91.0 and r["zone_high"] == 100.0
    assert r["mean_threshold"] == 95.5
    assert r["protected_swing"] == 90.0


def test_order_block_wick_zone_is_wider():
    body = order_blocks(bull_then_retest(), zone="body",
                        level_rule="series_extreme").iloc[0]
    wick = order_blocks(bull_then_retest(), zone="wick",
                        level_rule="series_extreme").iloc[0]
    assert wick["zone_low"] <= body["zone_low"]
    assert wick["zone_high"] >= body["zone_high"]
    assert (wick["zone_high"] - wick["zone_low"]) > (body["zone_high"] - body["zone_low"])


def test_zone_argument_validated():
    with pytest.raises(ValueError):
        order_blocks(bull_then_retest(), zone="midpoint")


def test_first_mitigation_found_and_threshold_measured():
    df = bull_then_retest()
    b = order_blocks(df, zone="body", level_rule="series_extreme")
    m = first_mitigation(df, b)
    r = m[m["direction"] == "bullish"].iloc[0]
    assert r["mitigated_at"] == df.index[8], "first re-entry into the zone is bar 8"
    assert r["bars_to_mitigation"] == 1
    # pandas stores this as np.True_, so compare by value rather than identity.
    assert bool(r["mean_threshold_held"]) is True, "bar 8 closed 99.5, above the 95.5 mid"


def test_mitigation_absent_when_price_never_returns():
    df = mk([
        (104, 105, 103, 104), (104, 105, 103, 104),
        (100, 101, 96, 97), (97, 98, 93, 94), (94, 95, 90, 91),
        (91, 91.6, 90.5, 90.9), (90.9, 91.4, 90.6, 90.95),
        (91, 101.5, 90.9, 101.2),
        (101.2, 110, 101.1, 109), (109, 115, 108, 114),
        (114, 120, 113, 119), (119, 125, 118, 124),
    ])
    b = order_blocks(df, zone="body", level_rule="series_extreme")
    m = first_mitigation(df, b)
    assert pd.isna(m.iloc[0]["mitigated_at"])


def test_block_validity_hinges_on_the_objective():
    df = bull_then_retest()
    b = order_blocks(df, zone="body", level_rule="series_extreme").iloc[0]
    later = df.index[10]
    # Objective untaken -> a re-tap is still valid.
    assert block_still_valid(b, later, None) is True
    # Objective already taken -> the corpus says the re-tap is the stop-out trap.
    assert block_still_valid(b, later, df.index[9]) is False


def test_block_not_valid_before_its_cisd_close():
    df = bull_then_retest()
    b = order_blocks(df, zone="body", level_rule="series_extreme").iloc[0]
    assert block_still_valid(b, df.index[3], None) is False


def test_protected_swing_chain_supersedes():
    df = bull_then_retest()
    ch = protected_swing_chain(df, direction="bullish", level_rule="series_extreme")
    assert len(ch) >= 1
    assert ch.iloc[0]["supersedes"] is None
    for i in range(1, len(ch)):
        assert ch.iloc[i]["supersedes"] == ch.iloc[i - 1]["protected_swing"]


def test_min_separation_rejects_equal_level_swings():
    """'A swing that forms at equal lows with the swept level is not tradeable.'"""
    df = bull_then_retest()
    loose = protected_swing_chain(df, direction="bullish", min_separation=0.0,
                                  level_rule="series_extreme")
    strict = protected_swing_chain(df, direction="bullish", min_separation=1e9,
                                   level_rule="series_extreme")
    assert len(strict) <= len(loose)
    assert len(strict) == 1, "an impossible separation keeps only the first swing"


def test_direction_validated():
    with pytest.raises(ValueError):
        protected_swing_chain(bull_then_retest(), direction="sideways")


def test_empty_inputs_are_safe():
    empty = pd.DataFrame(columns=["open", "high", "low", "close"])
    b = order_blocks(empty)
    assert b.empty
    assert first_mitigation(empty, b).empty
    assert protected_swing_chain(empty).empty


@pytest.mark.skipif(not (Path(__file__).resolve().parents[3] / "m3_scalper"
                         / "xau_m1_3y.parquet").exists(),
                    reason="XAUUSD parquet not available")
def test_real_data_blocks_are_plausible():
    from bars import load_m1, resample

    h1 = resample(load_m1(), "1h")
    b = order_blocks(h1, zone="body", level_rule="series_open", min_series=2)
    assert len(b) > 50
    assert (b["zone_high"] >= b["zone_low"]).all()
    assert (b["mean_threshold"].between(b["zone_low"], b["zone_high"])).all()

    m = first_mitigation(h1, b, max_bars=100)
    rate = m["mitigated_at"].notna().mean()
    assert 0.2 < rate < 1.0, f"implausible mitigation rate {rate:.2f}"
