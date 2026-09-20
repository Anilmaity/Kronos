"""Deterministic tests for the point-of-interest gate (§4.1).

Hand-built bar series with a KNOWN answer, so a failure means the detector is
wrong rather than the market being unusual. Real-data smoke checks live at the
bottom and are skipped when the parquet is absent.

Run:  python -m pytest detectors/test_poi.py -q      (from research/python)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detectors.poi import (  # noqa: E402
    POI_REQUIRED_ABOVE_DENSITY, cisd_level_poi, firing_rate, fvg_pois,
    poi_gate, poi_gate_events, poi_required, pois_in_range, range_from_swing,
    swing_pois,
)


def mk(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """rows of (open, high, low, close) -> 1-minute OHLC frame."""
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1min", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


# ── the density rule (§4.1 `poi-density-by-timeframe`) ────────────────────────
def test_hourly_requires_a_poi_and_four_hour_does_not():
    """The stated pair: ~24 hourly candles a day so the POI is the filter that
    says which one matters; six 4-hour candles a day so one without is fine."""
    assert poi_required("1h") is True
    assert poi_required("4h") is False
    assert POI_REQUIRED_ABOVE_DENSITY == 12.0     # sits between 6/day and 24/day


def test_continuation_waives_the_requirement():
    assert poi_required("1h", setup_type="continuation") is False
    assert poi_required("1h", setup_type="reversal") is True


def test_continuation_waiver_can_itself_be_switched_off():
    assert poi_required("1h", setup_type="continuation",
                        waive_for_continuation=False) is True


def test_master_switch_beats_everything():
    assert poi_required("1h", setup_type="reversal", enabled=False) is False


def test_unknown_timeframe_raises_rather_than_guessing():
    with pytest.raises(ValueError):
        poi_required("7min")


def test_bad_setup_type_raises():
    with pytest.raises(ValueError):
        poi_required("1h", setup_type="scalp")


# ── candidate finders ─────────────────────────────────────────────────────────
def test_fvg_in_the_range_is_found_and_tagged_by_the_extreme():
    # Overlapping bars, then one clean displacement leaving exactly one bearish
    # FVG on the last bar: high[4]=14 < low[2]=17.
    df = mk([(20, 21, 19, 20), (19, 20, 18, 19), (18, 19, 17, 18),
             (17, 18, 16, 17), (13, 14, 12, 13)])
    got = fvg_pois(df, 0, 4, "bullish")
    assert len(got) == 1
    assert got[0]["kind"] == "fvg"
    assert (got[0]["gap_low"], got[0]["gap_high"]) == (14.0, 17.0)
    assert got[0]["level"] == 17.0, "a bullish setup marks the gap's upper edge"
    assert got[0]["tagged"] is True, "the extreme low of 12 traded into the gap"


def test_fvg_above_an_extreme_that_never_reached_it_is_untagged():
    """`tagged` is engagement, not existence — §4.1's both-must-be-tagged clause
    only means anything on the engagement reading."""
    # Bullish gap on bar 2: low[2]=16 > high[0]=11, so the zone is 11..16.
    df = mk([(10, 11, 10, 11), (12, 15, 12, 15), (16, 17, 16, 17),
             (17, 18, 17, 18)])
    got = {p["gap_high"]: p for p in fvg_pois(df, 0, 3, "bullish")}
    assert 16.0 in got
    assert got[16.0]["tagged"] is False, "the low of 17 never came back to 16"
    assert got[17.0]["tagged"] is True, "this one the extreme sits exactly on"


def test_swing_low_taken_out_is_a_poi_for_a_bullish_setup():
    # lows 5,4,1,4,5 -> swing low at 2; then a deeper low at 6.
    df = mk([(0, 0, 5, 0), (0, 0, 4, 0), (0, 0, 1, 0), (0, 0, 4, 0),
             (0, 0, 5, 0), (0, 0, 4, 0), (0, 0, 0.5, 0)])
    got = swing_pois(df, 0, 6, "bullish")
    assert len(got) == 1 and got[0]["level"] == 1.0
    assert got[0]["tagged"] is True, "0.5 < 1.0, the low was taken"


def test_swing_not_taken_out_is_present_but_untagged():
    df = mk([(0, 0, 5, 0), (0, 0, 4, 0), (0, 0, 1, 0), (0, 0, 4, 0),
             (0, 0, 5, 0), (0, 0, 4, 0), (0, 0, 2, 0)])
    got = swing_pois(df, 0, 6, "bullish")
    assert len(got) == 1 and got[0]["tagged"] is False


def test_swing_needs_to_be_confirmable_before_the_extreme():
    """A swing confirmed only by bars at or after the extreme cannot have been a
    level anyone marked — that would be look-ahead."""
    df = mk([(0, 0, 5, 0), (0, 0, 4, 0), (0, 0, 1, 0), (0, 0, 4, 0)])
    assert swing_pois(df, 0, 3, "bullish") == []


def test_cisd_level_branch_uses_the_series_open_and_the_body_half():
    # Three down-close candles into a low, then two closes back above.
    df = mk([(10, 10, 9, 9), (9, 9, 8, 8), (8, 8, 7, 7),
             (7, 9, 7, 9), (9, 10, 9, 10)])
    got = cisd_level_poi(df, 0, 2, "bullish")
    assert got is not None
    assert got["level"] == 10.0            # open of the FIRST candle of the run
    assert got["series_len"] == 3
    assert got["body_half"] == 8.5         # bodies span 7..10
    assert got["body_half_held"] is True   # closes of 9 and 10 are above it


def test_cisd_level_branch_fails_when_the_body_half_does_not_hold():
    df = mk([(10, 10, 9, 9), (9, 9, 8, 8), (8, 8, 7, 7),
             (7, 7.5, 6, 6.5), (6.5, 7, 6, 6.2)])
    got = cisd_level_poi(df, 0, 2, "bullish")
    assert got is not None and got["body_half_held"] is False
    assert got["tagged"] is False


def test_cisd_branch_records_how_far_forward_it_looked():
    """The body-hold test waits by design, so availability must reflect it."""
    df = mk([(10, 10, 9, 9), (9, 9, 8, 8), (8, 8, 7, 7),
             (7, 9, 7, 9), (9, 10, 9, 10), (10, 11, 10, 11)])
    got = cisd_level_poi(df, 0, 2, "bullish", body_hold_bars=3)
    assert got["last_bar_used"] > got["series_end"]


# ── the gate's search order ───────────────────────────────────────────────────
def _fvg_and_swing_frame() -> pd.DataFrame:
    """A frame carrying BOTH a bearish FVG and a prior swing low."""
    return mk([
        (20, 21, 19, 20),      # 0
        (20, 20, 18, 18),      # 1
        (18, 18, 14, 14),      # 2  swing low candidate region
        (14, 16, 13, 15),      # 3  low 13 = the swing low
        (15, 17, 15, 16),      # 4
        (16, 17, 16, 17),      # 5
        (10, 11, 9, 10),       # 6  bearish FVG: high 11 < low[4] 15
        (10, 10, 8, 9),        # 7
        (9, 9, 7, 8),          # 8  the extreme
        (8, 10, 8, 10),        # 9
        (10, 11, 10, 11),      # 10
    ])


def test_when_both_exist_both_must_be_tagged():
    df = _fvg_and_swing_frame()
    res = poi_gate(df, 8, "bullish", range_start=0, timeframe="1h")
    assert res.kinds_found == ("fvg", "swing")
    assert res.kinds_required == ("fvg", "swing")
    assert res.passed is True and res.kind_used == "fvg+swing"


def test_the_loose_reading_accepts_either_one():
    df = _fvg_and_swing_frame()
    res = poi_gate(df, 8, "bullish", range_start=0, timeframe="1h",
                   require_both_when_both_exist=False)
    assert res.kinds_required == ("fvg|swing",)
    assert res.passed is True


def test_swing_branch_only_runs_when_there_is_no_fvg():
    # Overlapping ranges throughout -> no FVG anywhere.
    df = mk([(0, 10, 5, 6), (0, 10, 4, 6), (0, 10, 1, 6), (0, 10, 4, 6),
             (0, 10, 5, 6), (0, 10, 4, 6), (0, 10, 0.5, 6), (0, 10, 3, 6)])
    res = poi_gate(df, 6, "bullish", range_start=0, timeframe="1h")
    assert "fvg" not in res.kinds_found
    assert res.kinds_required == ("swing",)
    assert res.passed is True


def test_cisd_branch_is_the_last_resort():
    # Overlapping ranges (no FVG) and a range too short for a confirmable swing,
    # so only branch 3 is left.
    df = mk([(10, 10.2, 8.5, 9), (9, 9.2, 7.5, 8), (8, 8.6, 7.0, 7),
             (7, 9, 6.9, 9), (9, 10, 8.9, 10)])
    res = poi_gate(df, 2, "bullish", range_start=0, timeframe="1h")
    assert res.kinds_found == ()
    assert res.kinds_required == ("cisd_level",)
    assert res.passed is True and res.kind_used == "cisd_level"


def test_no_poi_at_all_fails_a_required_gate():
    df = mk([(5, 5, 5, 5)] * 8)
    res = poi_gate(df, 5, "bullish", range_start=0, timeframe="1h")
    assert res.required is True and res.passed is False


# ── the switch ────────────────────────────────────────────────────────────────
def test_disabled_gate_passes_but_still_reports_what_it_would_have_said():
    """The whole point of the switch: downstream code reports both ways."""
    df = mk([(5, 5, 5, 5)] * 8)
    res = poi_gate(df, 5, "bullish", range_start=0, timeframe="1h", enabled=False)
    assert res.required is False and res.passed is True
    assert "would have said False" in res.reason


def test_four_hour_without_a_poi_is_acceptable():
    df = mk([(5, 5, 5, 5)] * 8)
    res = poi_gate(df, 5, "bullish", range_start=0, timeframe="4h")
    assert res.required is False and res.passed is True
    assert res.kind_used is None


def test_continuation_is_waived_even_on_the_hourly():
    df = mk([(5, 5, 5, 5)] * 8)
    res = poi_gate(df, 5, "bullish", range_start=0, timeframe="1h",
                   setup_type="continuation")
    assert res.required is False and res.passed is True


# ── availability ──────────────────────────────────────────────────────────────
def test_gate_never_claims_to_have_looked_before_the_extreme():
    df = _fvg_and_swing_frame()
    res = poi_gate(df, 8, "bullish", range_start=0, timeframe="1h")
    assert res.detail["last_bar_used"] >= res.detail["extreme"]


def test_fvg_and_swing_branches_do_not_look_past_the_extreme():
    df = _fvg_and_swing_frame()
    res = poi_gate(df, 8, "bullish", range_start=0, timeframe="1h")
    assert res.detail["last_bar_used"] == res.detail["extreme"], \
        "only the CISD branch is allowed to wait"


def test_bars_after_the_extreme_cannot_change_an_fvg_or_swing_verdict():
    df = _fvg_and_swing_frame()
    before = poi_gate(df, 8, "bullish", range_start=0, timeframe="1h")
    hacked = df.copy()
    hacked.iloc[9:] = hacked.iloc[9:] * 100.0
    after = poi_gate(hacked, 8, "bullish", range_start=0, timeframe="1h")
    assert (before.passed, before.kind_used) == (after.passed, after.kind_used)


# ── plumbing ──────────────────────────────────────────────────────────────────
def test_range_from_swing_finds_the_opposing_swing():
    df = mk([(0, 1, 0, 0), (0, 5, 0, 0), (0, 9, 0, 0), (0, 5, 0, 0),
             (0, 1, 0, 0), (0, 1, -1, 0), (0, 1, -2, 0)])
    assert range_from_swing(df, 6, "bullish") == 2


def test_pois_in_range_returns_a_schema_even_when_empty():
    out = pois_in_range(mk([(5, 5, 5, 5)] * 6), 0, 4, "bullish")
    assert list(out.columns[:4]) == ["kind", "time", "level", "tagged"]


def test_poi_gate_events_keeps_every_row():
    df = _fvg_and_swing_frame()
    ev = pd.DataFrame({"extreme_time": [df.index[8]], "direction": ["bullish"]})
    out = poi_gate_events(df, ev, timeframe="1h")
    assert len(out) == 1 and "poi_passed" in out.columns


def test_empty_events_frame_survives():
    out = poi_gate_events(mk([(5, 5, 5, 5)] * 4),
                          pd.DataFrame(columns=["extreme_time", "direction"]))
    assert len(out) == 0 and "poi_passed" in out.columns


def test_direction_must_be_named():
    with pytest.raises(ValueError):
        poi_gate(mk([(5, 5, 5, 5)] * 6), 4, "up", range_start=0)


def test_bad_polarity_raises():
    with pytest.raises(ValueError):
        fvg_pois(mk([(5, 5, 5, 5)] * 6), 0, 4, "bullish", polarity="inverted")


# ── real-data smoke ───────────────────────────────────────────────────────────
_PARQUET = (Path(__file__).resolve().parents[3] / "m3_scalper" / "xau_m1_3y.parquet")


@pytest.mark.skipif(not _PARQUET.exists(), reason="XAUUSD parquet not available")
def test_real_data_gate_is_selective_but_not_empty():
    """Sanity, not correctness: on 3 years of real XAUUSD the gate must neither
    fire on everything nor on nothing, and switching it off must be strictly
    more permissive."""
    from bars import load_m1, resample
    from detectors.cisd import cisd_events

    h1 = resample(load_m1(), "1h")
    ev = cisd_events(h1).head(400)
    assert len(ev) > 50

    on = firing_rate(h1, ev, timeframe="1h")
    off = firing_rate(h1, ev, timeframe="1h", enabled=False)
    assert 0.0 < on["pass_rate"] < 1.0
    assert off["pass_rate"] == 1.0
    assert off["n"] == on["n"], "the switch changes verdicts, never the sample"
    assert on["n_passed"] <= off["n_passed"]
