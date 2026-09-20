"""Deterministic tests for the higher-timeframe bias layer (§2).

Hand-built bar series with a KNOWN answer, so a failure means the detector is
wrong rather than the market being unusual. Real-data smoke checks live at the
bottom and are skipped when the parquet is absent.

The most important test in this file is
`test_no_gate_reads_past_its_availability`: it perturbs every bar after a gate's
claimed `*_available_at` and asserts the verdict does not move. Look-ahead is
silent — a gate that peeks at the bar it fires on manufactures an edge that looks
like success — so it has to be caught mechanically rather than by reading code.

Run:  python -m pytest detectors/test_bias.py -q      (from research/python)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detectors import bias as B  # noqa: E402


def mk(rows, freq="1min", start="2024-01-01", tz="UTC"):
    idx = pd.date_range(start, periods=len(rows), freq=freq, tz=tz)
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def walk(n: int, seed: int = 7, start="2024-02-01") -> pd.DataFrame:
    """A seeded M1 random walk — structure-free, but enough to exercise plumbing."""
    rng = np.random.default_rng(seed)
    step = rng.normal(0, 0.35, n).cumsum() + 2000.0
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    o = pd.Series(step, index=idx)
    c = o.shift(-1).fillna(o.iloc[-1])
    wig = np.abs(rng.normal(0, 0.25, n))
    return pd.DataFrame({"open": o, "close": c,
                         "high": np.maximum(o, c) + wig,
                         "low": np.minimum(o, c) - wig}, index=idx)


# ── the clock (settled in phase 2 — these tests pin it, they do not sweep it) ──
def test_trading_day_anchors_on_eighteen_hundred_new_york():
    idx = pd.DatetimeIndex(["2024-03-04 22:30", "2024-03-05 02:00",
                            "2024-03-05 21:30"], tz="UTC")
    # 22:30Z = 17:30 NY (previous day's session); 02:00Z next = 21:00 NY same
    # session; 21:30Z = 16:30 NY, still the same session.
    days = B.trading_day(idx)
    assert days[0] != days[1]
    assert days[1] == days[2]


def test_trading_day_survives_the_dst_switch():
    """Wall-clock arithmetic, not fixed UTC offsets: the venue's break resumes at
    18:00 NY on both sides of the switch (`meta/session_window_fit.md`)."""
    before = pd.DatetimeIndex(["2024-03-08 23:00"], tz="UTC")   # 18:00 EST
    after = pd.DatetimeIndex(["2024-03-15 22:00"], tz="UTC")    # 18:00 EDT
    assert B.trading_day(before)[0] == pd.Timestamp("2024-03-08")
    assert B.trading_day(after)[0] == pd.Timestamp("2024-03-15")


def test_forex_four_hour_grid_opens_on_the_stated_hours():
    df = walk(60 * 24 * 5)
    h4 = B.four_hour_candles(df, grid="forex")
    assert sorted(set(h4["grid_open_local"].dt.hour)) == [1, 5, 9, 13, 17, 21]


def test_futures_grid_is_the_other_one_and_is_selectable():
    df = walk(60 * 24 * 5)
    h4 = B.four_hour_candles(df, grid="futures")
    assert sorted(set(h4["grid_open_local"].dt.hour)) == [2, 6, 10, 14, 18, 22]


def test_gold_defaults_to_the_forex_grid():
    assert B.DEFAULT_GRID == "forex"
    assert B.FOUR_HOUR_GRID_OFFSETS["forex"] == 1


def test_four_hour_index_stays_timezone_aware():
    h4 = B.four_hour_candles(walk(60 * 24 * 3))
    assert h4.index.tz is not None


def test_bad_grid_raises():
    with pytest.raises(ValueError):
        B.four_hour_candles(walk(200), grid="crypto")


def test_daily_candles_carry_a_close_time_not_just_a_left_label():
    d = B.daily_candles(walk(60 * 24 * 4))
    assert (d["utc_end_close"] > d["utc_end"]).all()


# ── §3.6 wick geometry ────────────────────────────────────────────────────────
def test_opposing_run_is_one_sided_from_the_open():
    """Settled: *"from the opening price to that high"* — not high-low, not the
    sum of both wicks."""
    df = mk([(10, 14, 8, 12)])
    assert B.opposing_run(df, "bullish").iloc[0] == 2.0      # open 10 -> low 8
    assert B.opposing_run(df, "bearish").iloc[0] == 4.0      # open 10 -> high 14


def test_small_wick_default_cut_is_the_grade_a_one():
    assert B.WICK_CUT_BODY == 1.0
    df = mk([(10, 12, 9.5, 12)])           # run 0.5, body 2.0 -> ratio 0.25
    assert bool(B.is_small_wick(df, "bullish").iloc[0]) is True


def test_large_opposing_run_fails_the_expansion_test():
    df = mk([(10, 11, 5, 10.5)])           # run 5.0, body 0.5 -> ratio 10
    assert bool(B.is_small_wick(df, "bullish").iloc[0]) is False


def test_wick_measure_range_uses_its_own_default():
    assert B.WICK_CUT_RANGE == 0.30
    df = mk([(10, 12, 9.5, 12)])           # run 0.5, range 2.5 -> 0.2
    assert bool(B.is_small_wick(df, "bullish", measure="range").iloc[0]) is True


# ── §2.3 the previous-candle engine ───────────────────────────────────────────
def test_continuation_closure_anticipates_the_same_direction():
    df = mk([(10, 12, 8, 11), (11, 14, 10, 13)])       # took the high, closed out
    out = B.previous_candle_state(df)
    assert out["state"].iloc[1] == "continuation"
    assert out["implied_bias"].iloc[1] == "bullish"


def test_reversal_closure_anticipates_the_opposite():
    df = mk([(10, 12, 8, 11), (11, 13, 10, 11.5)])     # took the high, closed in
    out = B.previous_candle_state(df)
    assert out["state"].iloc[1] == "reversal"
    assert out["implied_bias"].iloc[1] == "bearish"


def test_both_sides_taken_is_no_bias():
    df = mk([(10, 12, 8, 11), (11, 13, 7, 10)])
    out = B.previous_candle_state(df)
    assert out["state"].iloc[1] == "both"
    assert out["implied_bias"].iloc[1] == "none"


def test_inside_bar_defaults_to_the_trend():
    df = mk([(10, 12, 8, 11), (11, 14, 10, 13), (12, 13, 11, 12)])
    out = B.previous_candle_state(df)
    assert out["state"].iloc[2] == "inside"
    assert out["implied_bias"].iloc[2] == "bullish", "carried from the last resolution"


def test_three_inside_bars_become_range_bound_and_stand_aside():
    df = mk([(10, 20, 0, 15)] + [(12, 13, 11, 12)] * 3)
    out = B.previous_candle_state(df, range_lookback=3)
    assert out["state"].iloc[3] == "range_bound"
    assert out["implied_bias"].iloc[3] == "none"


def test_eq_of_the_previous_range_is_marked():
    df = mk([(10, 12, 8, 11), (11, 13, 10, 11.5)])
    assert B.previous_candle_state(df)["prev_eq"].iloc[1] == 10.0


# ── §2.2 the draw ─────────────────────────────────────────────────────────────
def test_proximity_draw_picks_the_nearer_pool():
    df = mk([(10, 20, 0, 10), (19, 19, 18, 19)])       # opens at 19, high pool 20
    out = B.draw_on_liquidity(df, rule="proximity", lookback=1)
    assert out["draw"].iloc[1] == "buyside"


def test_displacement_draw_follows_the_previous_close():
    df = mk([(10, 12, 8, 8.5), (9, 10, 8, 9)])        # previous candle closed down
    out = B.draw_on_liquidity(df, rule="displacement")
    assert out["draw"].iloc[1] == "sellside"


def test_bias_draw_needs_the_bias_series():
    with pytest.raises(ValueError):
        B.draw_on_liquidity(mk([(1, 1, 1, 1)] * 3), rule="bias")


def test_bad_draw_rule_raises():
    with pytest.raises(ValueError):
        B.draw_on_liquidity(mk([(1, 1, 1, 1)] * 3), rule="vibes")


# ── §3.2 / §3.3 closures ──────────────────────────────────────────────────────
def test_c3_closure_only_exists_where_c2_failed_to_close():
    """Without that precondition the test degenerates to "did this candle close
    beyond the last one's open", which fires on ~75% of daily candles."""
    # candle 1 takes the low and closes BELOW it -> a failed C2, an expansion.
    # candle 2 then closes back above candle 1's open -> a C3 closure.
    df = mk([(10, 12, 8, 11), (11, 11.5, 6, 7), (7, 13, 7, 12)])
    out = B.daily_closures(df)
    assert out["c2_closure"].iloc[1] == "none"
    assert out["c3_closure"].iloc[2] == "bullish"
    assert out["closure_kind"].iloc[2] == "C3"


def test_c3_extreme_reading_is_strictly_stronger():
    # The failed C2 opened at 11 and topped at 11.5; C3 closes at 11.2 — beyond the
    # open (Reading A) but not beyond the extreme (Reading B).
    df = mk([(10, 12, 8, 11), (11, 11.5, 6, 7), (7, 11.4, 7, 11.2)])
    a = B.daily_closures(df, c3_reference="c2_open")
    b = B.daily_closures(df, c3_reference="c2_extreme")
    assert a["c3_closure"].iloc[2] == "bullish"
    assert b["c3_closure"].iloc[2] == "none"


def test_bad_c3_reference_raises():
    with pytest.raises(ValueError):
        B.daily_closures(mk([(1, 1, 1, 1)] * 3), c3_reference="c2_midpoint")


# ── §2.4 the hourly CISD ──────────────────────────────────────────────────────
def _cisd_frame():
    # opens high, three down-close candles into a low, then closes back through
    # the first candle's open (10).
    return mk([(10, 10.2, 9, 9), (9, 9.2, 8, 8), (8, 8.2, 7, 7),
               (7, 9, 6.9, 8.5), (8.5, 11, 8.4, 10.5)], freq="1h")


def test_hourly_cisd_confirms_on_a_close_through_the_series_open():
    df = _cisd_frame()
    ev = B.hourly_cisd_in_candle(df, df.index[0], df.index[-1], "bullish")
    assert ev is not None
    assert ev["level"] == 10.0            # open of the FIRST candle of the run
    assert ev["series_len"] == 3
    assert ev["confirm_time"] == df.index[4]


def test_no_close_through_means_no_confirmation():
    df = mk([(10, 10.2, 9, 9), (9, 9.2, 8, 8), (8, 8.2, 7, 7),
             (7, 7.5, 6.9, 7.2), (7.2, 7.6, 7, 7.4)], freq="1h")
    assert B.hourly_cisd_in_candle(df, df.index[0], df.index[-1], "bullish") is None


def test_speed_test_can_reject_a_slow_closure():
    """§4.2's only candle-count threshold — *"I prefer 1, 2, maybe three"* — is a
    stated preference, so it is off by default and on by request."""
    df = _cisd_frame()
    assert B.hourly_cisd_in_candle(df, df.index[0], df.index[-1], "bullish",
                                   max_bars_waited=3) is not None
    assert B.hourly_cisd_in_candle(df, df.index[0], df.index[-1], "bullish",
                                   max_bars_waited=1) is None


def test_wick_scope_needs_the_htf_open():
    df = _cisd_frame()
    with pytest.raises(ValueError):
        B.hourly_cisd_in_candle(df, df.index[0], df.index[-1], "bullish",
                                scope="wick")


def test_bad_cisd_scope_and_level_rule_raise():
    df = _cisd_frame()
    with pytest.raises(ValueError):
        B.hourly_cisd_in_candle(df, df.index[0], df.index[-1], "bullish",
                                scope="body")
    with pytest.raises(ValueError):
        B.hourly_cisd_in_candle(df, df.index[0], df.index[-1], "bullish",
                                level_rule="midpoint")


# ── §2.5 the profile support gate ─────────────────────────────────────────────
def test_profile_must_agree_with_the_bias():
    prof = pd.Series(["london_reversal", "london_reversal"])
    pdir = pd.Series(["bullish", "bearish"])
    bias = pd.Series(["bullish", "bullish"])
    assert list(B.profile_supports_bias(prof, pdir, bias)) == [True, False]


def test_seek_and_destroy_never_supports_anything():
    """A stand-aside day by name — the bias may stand, the entry does not."""
    out = B.profile_supports_bias(pd.Series(["seek_and_destroy"]),
                                  pd.Series(["bullish"]), pd.Series(["bullish"]))
    assert list(out) == [False]


def test_unclassified_is_not_permission_by_default():
    args = (pd.Series(["unclassified"]), pd.Series(["none"]), pd.Series(["bullish"]))
    assert list(B.profile_supports_bias(*args)) == [False]
    assert list(B.profile_supports_bias(*args, unclassified_supports=True)) == [True]


# ── §2.1 / §3.5 alignment ─────────────────────────────────────────────────────
def _row(o, h, l, c):
    return pd.Series({"open": o, "high": h, "low": l, "close": c})


def test_two_aligned_layers_is_the_stated_minimum():
    up = _row(10, 12, 9.9, 12)              # bullish body, tiny opposing run
    res = B.timeframe_alignment("bullish", up, up, None)
    assert res["n_aligned"] == 2 and res["passed"] is True


def test_one_aligned_layer_is_not_enough():
    up = _row(10, 12, 9.9, 12)
    flat = _row(10, 10.1, 8, 9)             # bearish body
    res = B.timeframe_alignment("bullish", up, flat, flat)
    assert res["n_aligned"] == 1 and res["passed"] is False


def test_no_fading_the_daily_candle_overrides_a_passing_count():
    """§2.1's separate hard gate: the daily layer may not oppose, however many
    other layers agree."""
    up = _row(10, 12, 9.9, 12)
    down = _row(12, 12.1, 9, 10)
    res = B.timeframe_alignment("bullish", down, up, up)
    assert res["daily_opposes"] is True and res["passed"] is False
    loose = B.timeframe_alignment("bullish", down, up, up, no_fade_daily=False)
    assert loose["passed"] is True


def test_a_layer_with_a_large_wick_does_not_count():
    small = _row(10, 12, 9.9, 12)
    big_wick = _row(10, 12, 4, 11)          # run 6, body 1 -> ratio 6
    res = B.timeframe_alignment("bullish", small, big_wick, big_wick)
    assert res["n_aligned"] == 1


# ── §2.6 SMT / PSP ────────────────────────────────────────────────────────────
def _smt_frames():
    """`a` sweeps its swing low of 1.0 at bar 5; `b` holds at 2.0. One shared
    moment (bar 2), one shared level, one asset beyond it."""
    lows = [5, 4, 1, 4, 5, 0.5, 3, 3, 3, 3]
    a = mk([(0, 6, x, 0) for x in lows], freq="1h")
    b = a.copy()
    b.iloc[5, b.columns.get_loc("low")] = 2.0
    return a, b


def test_smt_fires_when_one_asset_makes_the_low_and_the_other_holds():
    a, b = _smt_frames()
    ev = B.smt_events(a, b, lookback=3, names=("gold", "silver"))
    bull = ev[ev["direction"] == "bullish"]
    assert len(bull) == 1
    row = bull.iloc[0]
    assert row["swept_by"] == "gold" and row["held_by"] == "silver"
    assert row["ref_time"] == a.index[2]
    assert row["invalidation"] == 1.0, "the held low of the diverging asset"


def test_smt_does_not_fire_when_both_assets_go():
    a, _ = _smt_frames()
    assert B.smt_events(a, a.copy(), lookback=3).empty


def test_smt_refuses_mismatched_bar_widths():
    """Comparing a 1h label against a 4h label is not one shared level in time."""
    a = mk([(0, 6, 5, 0)] * 30, freq="1h")
    b = mk([(0, 6, 5, 0)] * 30, freq="4h")
    with pytest.raises(ValueError):
        B.smt_events(a, b)


def test_smt_events_carry_an_availability_stamp_one_bar_after_the_label():
    a, b = _smt_frames()
    ev = B.smt_events(a, b, lookback=3)
    assert len(ev) and (ev["available_at"] - ev["time"] == pd.Timedelta(hours=1)).all()


def test_smt_gate_ignores_divergence_with_no_model_behind_it():
    """§2.6 doctrine: you find the model and *then* check for SMT."""
    ev = pd.DataFrame({"time": pd.to_datetime(["2024-01-01 05:00"], utc=True),
                       "direction": ["bullish"]})
    far = pd.to_datetime(["2024-01-01 20:00"], utc=True)
    assert bool(B.smt_gate(ev, far, window=3,
                           freq=pd.Timedelta(hours=1))["smt_confirmed"].iloc[0]) is False
    near = pd.to_datetime(["2024-01-01 06:00"], utc=True)
    assert bool(B.smt_gate(ev, near, window=3,
                           freq=pd.Timedelta(hours=1))["smt_confirmed"].iloc[0]) is True


def test_smt_standalone_is_off_by_default_and_available_on_request():
    ev = pd.DataFrame({"time": pd.to_datetime(["2024-01-01 05:00"], utc=True),
                       "direction": ["bullish"]})
    out = B.smt_gate(ev, [], standalone_allowed=True)
    assert bool(out["smt_confirmed"].iloc[0]) is True
    assert bool(B.smt_gate(ev, [])["smt_confirmed"].iloc[0]) is False


def test_psp_is_opposite_closes_on_the_same_candle():
    a = mk([(10, 11, 9, 11), (11, 12, 10, 10)], freq="1h")
    b = mk([(10, 11, 9, 9), (10, 12, 9, 11)], freq="1h")
    assert list(B.psp(a, b)) == [True, True]
    assert list(B.psp(a, a.copy())) == [False, False]


# ── availability / look-ahead ─────────────────────────────────────────────────
def test_daily_bias_is_not_available_before_the_day_closes():
    m1 = walk(60 * 24 * 30, seed=11)
    daily = B.daily_candles(m1)
    h1 = B._resample(m1, "1h")
    bf = B.daily_bias(daily, h1)
    live = bf[bf["bias"] != "none"]
    assert len(live) > 0, "the fixture must actually produce some biased days"
    assert (live["bias_available_at"] >= live["utc_end_close"]).all()


def test_no_gate_reads_past_its_availability():
    """THE look-ahead test. Perturb every bar strictly after a day's claimed
    availability moment and assert that day's verdicts are byte-identical.

    A gate that peeked at the next day's data — or at the close of the bar it
    fires on — would move here, and nowhere else that is easy to see."""
    m1 = walk(60 * 24 * 30, seed=3)
    xag = m1 * 1.0
    xag[["open", "high", "low", "close"]] = m1[["open", "high", "low", "close"]] / 80.0

    base = B.bias_report(m1, correlate_h1=B._resample(xag, "1h"))
    live = base[base["bias"] != "none"]
    assert len(live) >= 3, "need a few biased days for this to mean anything"

    day = live.index[len(live) // 2]
    cutoff = base.loc[day, "gates_available_at"]

    hacked = m1.copy()
    after = hacked.index >= cutoff
    assert after.sum() > 100, "the cutoff must leave real data to corrupt"
    hacked.loc[after, ["open", "high", "low", "close"]] *= 1.5
    hacked_xag = hacked.copy()
    hacked_xag[["open", "high", "low", "close"]] /= 80.0

    after_rep = B.bias_report(hacked, correlate_h1=B._resample(hacked_xag, "1h"))

    cols = ["bias", "branch", "profile", "profile_direction",
            "gate_bias", "gate_profile", "gate_alignment", "gate_poi", "gate_smt"]
    for c in cols:
        assert base.loc[day, c] == after_rep.loc[day, c], \
            f"{c} moved when only post-availability bars changed — look-ahead"


def test_next_day_view_shifts_the_verdict_forward_one_session():
    m1 = walk(60 * 24 * 20, seed=5)
    rep = B.bias_report(m1)
    nxt = B.next_day_view(rep)
    assert nxt["bias"].iloc[3] == rep["bias"].iloc[2]


# ── real-data smoke ───────────────────────────────────────────────────────────
_RD = Path(__file__).resolve().parents[3]
_M1 = _RD / "m3_scalper" / "xau_m1_3y.parquet"
_XAG = _RD / "m3_scalper" / "xag_h1.parquet"


@pytest.mark.skipif(not _M1.exists(), reason="XAUUSD parquet not available")
def test_real_data_gates_are_selective_but_not_empty():
    """Sanity, not correctness: on 3 years of real XAUUSD each gate must fire on
    a plausible minority of days, and stacking must be monotone."""
    from bars import load_m1

    rep = B.bias_report(load_m1())
    assert len(rep) > 700
    for g in ("gate_bias", "gate_profile", "gate_alignment", "gate_poi"):
        rate = rep[g].fillna(False).mean()
        assert 0.0 < rate < 0.9, f"{g} fired on {rate:.1%} of days"
    assert rep["gate_all"].sum() <= rep["gate_bias"].sum()


@pytest.mark.skipif(not (_M1.exists() and _XAG.exists()),
                    reason="correlate parquet not available")
def test_silver_shares_gold_bar_labels_so_smt_compares_like_with_like():
    """The alignment hazard the whole SMT layer rests on: both feeds are
    left-labelled at the same width, so the same label is the same close window."""
    from bars import load_m1

    h1 = B._resample(load_m1(), "1h")
    xag = pd.read_parquet(_XAG)
    assert B.infer_freq(h1.index) == B.infer_freq(xag.index)
    shared = h1.index.intersection(xag.index)
    assert len(shared) / len(h1) > 0.95
    assert set(pd.DatetimeIndex(shared).minute) == {0}
