"""Tests for the conjunction backtest.

These are not about the numbers being pretty. They are about the conventions the
pre-registration locks being the ones the code actually implements, because every
one of them is a convention whose violation produces a plausible-looking result
rather than an error:

  * entry one bar after the signal, because the other direction returns ~3% and
    reads as a bad strategy while the direction after that manufactures an edge;
  * same-bar ties taken as the stop, because M1 carries no intrabar order;
  * a control matched on direction, stop distance, target distance and a +/-30-day
    window, because an unmatched control inflates the rungs UNEQUALLY;
  * a gate's verdict used only once it has resolved, because the POI gate's third
    branch genuinely resolves after the event it qualifies;
  * the ladder's rungs nested, because a "leave-one-out" that is not a superset of
    the full model is not a leave-one-out.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# The module memoises expensive stages to disk. Tests must never read or write
# that cache: a stale entry would make a green suite meaningless.
os.environ["CONJ_CACHE_DISABLE"] = "1"

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest_conjunction import (  # noqa: E402
    GATES, MAX_HOLD, POWER_FLOOR_5PP, RUNGS, SWING_RIGHT,
    Book, _block_boot, body_extreme_stops, build_trades, calendar_blocks,
    ci_p, cisd_events_max_open, gate_matrix, holm, label_transition,
    matched_control, poi_annotate, rung_masks, sanity_flags, target_levels,
    verdict_for,
)
from backtest_c2_wick import apply_cost, resolve  # noqa: E402
from bars import resample  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402


# ── fixtures ──────────────────────────────────────────────────────────────────
def _m1(n: int = 4000, seed: int = 7) -> pd.DataFrame:
    """A synthetic M1 series with enough structure to make swings and gaps."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-03-04 00:00", periods=n, freq="1min", tz="UTC")
    step = rng.normal(0, 0.25, n).cumsum() + 2000.0
    hi = step + np.abs(rng.normal(0, 0.15, n))
    lo = step - np.abs(rng.normal(0, 0.15, n))
    op = np.concatenate([[step[0]], step[:-1]])
    return pd.DataFrame({"open": op, "high": np.maximum(hi, np.maximum(op, step)),
                         "low": np.minimum(lo, np.minimum(op, step)),
                         "close": step}, index=idx)


@pytest.fixture(scope="module")
def book():
    m1 = _m1()
    bars = resample(m1, "15min")
    ev = cisd_events(bars, level_rule="series_open", max_wait=3, min_series=1)
    tr = build_trades(ev, m1, bars, resample(m1, "1h"), "15min")
    return m1, bars, ev, tr


# ── the entry-timing convention ───────────────────────────────────────────────
def test_entry_is_one_bar_after_the_signal_never_on_it(book):
    """The off-by-one that returns a 3% win rate in one direction and a fake edge
    in the other. `i0` must index the first M1 bar at or after the signal bar's
    CLOSE, which under a left label is `confirm_time + one period`."""
    m1, _, _, tr = book
    assert len(tr) > 20
    first = m1.index[tr["i0"].to_numpy()]
    need = pd.DatetimeIndex(tr["time"]) + pd.Timedelta("15min")
    assert (first >= need).all()
    # and never earlier than the signal bar's own start
    assert (first > pd.DatetimeIndex(tr["time"])).all()


def test_the_signal_bar_itself_is_never_inside_the_resolution_window(book):
    m1, _, _, tr = book
    for k in range(min(len(tr), 50)):
        window = m1.index[tr["i0"].iloc[k]:tr["i1"].iloc[k]]
        assert window.min() >= tr["time"].iloc[k] + pd.Timedelta("15min")


def test_hold_window_is_max_hold_periods_long(book):
    m1, _, _, tr = book
    span = pd.Timedelta("15min") * MAX_HOLD
    for k in range(min(len(tr), 50)):
        w = m1.index[tr["i0"].iloc[k]:tr["i1"].iloc[k]]
        assert (w.max() - tr["time"].iloc[k]) <= span + pd.Timedelta("15min")


def test_cisd_confirm_bar_is_after_the_swing_could_be_confirmed(book):
    """A 3-bar fractal is not knowable until `right` bars after it prints."""
    _, _, ev, _ = book
    lag = pd.Timedelta("15min") * (SWING_RIGHT + 1)
    assert (pd.DatetimeIndex(ev["confirm_time"])
            >= pd.DatetimeIndex(ev["extreme_time"]) + lag).all()


# ── resolution conventions ────────────────────────────────────────────────────
def test_same_bar_stop_and_target_resolves_as_the_stop():
    """M1 gives no intrabar order; assuming otherwise manufactures edge."""
    idx = pd.date_range("2024-01-01", periods=3, freq="1min", tz="UTC")
    bars = pd.DataFrame({"open": [100.0, 100.0, 100.0],
                         "high": [100.0, 120.0, 100.0],
                         "low": [100.0, 80.0, 100.0],
                         "close": [100.0, 100.0, 100.0]}, index=idx)
    tr = pd.DataFrame({"time": [idx[0]], "long": [True], "entry": [100.0],
                       "stop": [90.0], "risk": [10.0], "i0": [1], "i1": [3],
                       "ev_i": [0], "atr20": [1.0]})
    res = resolve(tr, np.array([120.0]), bars, tie="stop")
    assert res["reason"].iloc[0] == "stop"


def test_a_bar_opening_through_the_stop_fills_at_that_open():
    idx = pd.date_range("2024-01-01", periods=3, freq="1min", tz="UTC")
    bars = pd.DataFrame({"open": [100.0, 85.0, 85.0], "high": [100.0, 86.0, 86.0],
                         "low": [100.0, 84.0, 84.0], "close": [100.0, 85.0, 85.0]},
                        index=idx)
    tr = pd.DataFrame({"time": [idx[0]], "long": [True], "entry": [100.0],
                       "stop": [90.0], "risk": [10.0], "i0": [1], "i1": [3],
                       "ev_i": [0], "atr20": [1.0]})
    res = resolve(tr, np.array([120.0]), bars, tie="stop")
    assert res["exit_px"].iloc[0] == pytest.approx(85.0)   # gap risk is paid


# ── targets ───────────────────────────────────────────────────────────────────
def test_fixed_r_targets_are_signed_by_direction():
    tr = pd.DataFrame({"long": [True, False], "entry": [100.0, 100.0],
                       "risk": [5.0, 5.0], "struct_target": [np.nan, np.nan]})
    assert list(target_levels(tr, "2R")) == [110.0, 90.0]


def test_a_structural_target_already_behind_the_entry_is_not_a_trade():
    """§1.12's structural target is the reference candle's UNSWEPT extreme. Once
    price has closed beyond it there is nothing left to deliver to, and quietly
    keeping the trade would credit a target the entry has already passed — the
    exact family of confounded metric §4.7 forbids."""
    tr = pd.DataFrame({"long": [True, True], "entry": [100.0, 100.0],
                       "risk": [5.0, 5.0], "struct_target": [105.0, 95.0]})
    lv = target_levels(tr, "structural")
    assert lv[0] == 105.0
    assert np.isnan(lv[1])


# ── the matched control ───────────────────────────────────────────────────────
def test_control_matches_direction_and_stop_distance_exactly(book):
    m1, bars, ev, tr = book
    tgt = target_levels(tr, "2R")
    ctrl, ctgt = matched_control(tr, tgt, bars, m1, "15min")
    src = tr.set_index("ev_i")
    assert (ctrl["long"].to_numpy()
            == src.loc[ctrl["ev_i"], "long"].to_numpy()).all()
    assert np.abs(ctrl["risk"].to_numpy()
                  - src.loc[ctrl["ev_i"], "risk"].to_numpy()).max() == 0.0
    # target distance identical in price
    d_ctrl = np.abs(ctgt - ctrl["entry"].to_numpy())
    d_real = np.abs(tgt - tr["entry"].to_numpy())
    assert np.abs(d_ctrl - pd.Series(d_real, index=tr["ev_i"])
                  .loc[ctrl["ev_i"]].to_numpy()).max() < 1e-9


def test_control_entries_lie_inside_the_locked_30_day_window(book):
    """+/-30 days is locked and may not be swept: gold ran ~1,100 to ~5,500 across
    the span, so a control drawn from the whole period is matched in USD but not
    in volatility — and it inflates the rungs unequally, which is fatal to a
    ladder specifically."""
    m1, bars, ev, tr = book
    ctrl, _ = matched_control(tr, target_levels(tr, "2R"), bars, m1, "15min")
    assert ctrl["offset_days"].abs().max() <= 30.0


def test_control_has_reps_times_the_real_trades(book):
    m1, bars, ev, tr = book
    ctrl, _ = matched_control(tr, target_levels(tr, "2R"), bars, m1, "15min",
                              reps=5)
    assert ctrl["rep"].nunique() == 5
    assert len(ctrl) <= 5 * len(tr)


def test_control_is_reproducible_from_its_seed(book):
    m1, bars, ev, tr = book
    a, _ = matched_control(tr, target_levels(tr, "2R"), bars, m1, "15min")
    b, _ = matched_control(tr, target_levels(tr, "2R"), bars, m1, "15min")
    assert (a["time"].to_numpy() == b["time"].to_numpy()).all()


# ── the ladder ────────────────────────────────────────────────────────────────
def _fake_gates(n=200, seed=3):
    rng = np.random.default_rng(seed)
    g = {k: rng.random(n) < 0.6 for k in GATES}
    g.update({"poi_raw": g["poi"], "smt": rng.random(n) < 0.1,
              "session": rng.random(n) < 0.2})
    return g


def test_forward_rungs_are_nested():
    n = 200
    m = rung_masks(_fake_gates(n), n)
    for a, b in zip(RUNGS, RUNGS[1:]):
        assert (m[b] & ~m[a]).sum() == 0, f"{b} is not a subset of {a}"


def test_leave_one_out_is_a_superset_of_the_full_model():
    n = 200
    m = rung_masks(_fake_gates(n), n)
    for gname in GATES:
        assert (m["R4"] & ~m[f"LOO-{gname}"]).sum() == 0
        assert m[f"LOO-{gname}"].sum() >= m["R4"].sum()


def test_knob_rungs_sit_inside_the_full_model():
    n = 200
    m = rung_masks(_fake_gates(n), n)
    for k in ("K1 session", "K2 SMT", "K3 session+SMT"):
        assert (m[k] & ~m["R4"]).sum() == 0


# ── the POI availability guard ────────────────────────────────────────────────
def test_poi_verdict_is_dropped_when_it_resolves_after_the_entry(book):
    """§4.1's third POI branch waits `body_hold_bars` past the opposing series to
    see whether 50% of the bodies hold. With `max_wait=3` that test can resolve
    AFTER the CISD it is supposed to qualify. A verdict that is not available at
    the entry moment is not a gate that passed — it is a gate that had not been
    evaluated yet."""
    m1, bars, ev, _ = book
    poi = poi_annotate(bars, ev, "15min", "test")
    late = ~poi["poi_in_time"].to_numpy()
    assert not (poi["poi_passed"].to_numpy() & late).any()
    # the guard is a restriction, never an addition
    assert (poi["poi_passed"].to_numpy()
            <= poi["poi_passed_raw"].to_numpy()).all()
    used = poi["poi_passed"].to_numpy()
    if used.any():
        lb = pd.DatetimeIndex(poi["poi_last_bar_used"])[used]
        conf = pd.DatetimeIndex(ev["confirm_time"])[used]
        assert (lb <= conf).all()


# ── the alternative CISD level reading ────────────────────────────────────────
def test_series_max_open_is_a_legal_level_and_never_looser_than_first_open():
    """For a bullish setup the run is down-close candles, so the highest open of
    the run is at or above the first candle's open — the secondary reading is
    weakly STRICTER, which is why it nests."""
    m1 = _m1(6000, seed=11)
    bars = resample(m1, "15min")
    a = cisd_events(bars, level_rule="series_open", max_wait=3, min_series=1)
    b = cisd_events_max_open(bars, max_wait=3, min_series=1)
    assert len(b) > 0
    key = ["direction", "extreme_time"]
    ja = a.set_index(key)["level"]
    jb = b.set_index(key)["level"]
    common = ja.index.intersection(jb.index)
    bull = [i for i in common if i[0] == "bullish"]
    if bull:
        assert (jb.loc[bull].to_numpy() >= ja.loc[bull].to_numpy() - 1e-9).all()


# ── the declared secondary stop ───────────────────────────────────────────────
def test_body_extreme_stop_is_inside_the_swing_it_replaces(book):
    """§1.11's secondary stop is the BODY extreme of the opposing series, which
    always sits at or inside the protected swing — bodies are contained by wicks.
    A 'tighter' stop that came out wider would be a sign extraction bug."""
    m1, bars, ev, tr = book
    st = body_extreme_stops(ev, bars)
    bull = (ev["direction"] == "bullish").to_numpy()
    swing = ev["protected_swing"].to_numpy(float)
    assert (st[bull] >= swing[bull] - 1e-9).all()
    assert (st[~bull] <= swing[~bull] + 1e-9).all()


# ── statistics ────────────────────────────────────────────────────────────────
def test_block_bootstrap_preserves_pairing_across_arrays():
    """The real trades and their matched controls must be resampled by the SAME
    blocks, or the comparison stops being paired and the CI is wrong."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    ma, mb = _block_boot([x, x], 200, np.random.default_rng(1))
    assert np.abs(ma - mb).max() < 1e-12


def test_block_bootstrap_means_are_centred_on_the_sample_mean():
    rng = np.random.default_rng(0)
    x = rng.normal(1.0, 2.0, size=3000)
    (m,) = _block_boot([x], 1000, np.random.default_rng(2))
    assert abs(m.mean() - x.mean()) < 0.15
    assert m.std() > 0


def test_block_bootstrap_is_wider_than_iid_on_autocorrelated_data():
    """The whole reason §4.5 adds it: overlapping trades make the i.i.d.
    bootstrap optimistic."""
    rng = np.random.default_rng(4)
    e = rng.normal(size=4000)
    x = pd.Series(e).rolling(50, min_periods=1).mean().to_numpy()   # strong AC
    (mb,) = _block_boot([x], 2000, np.random.default_rng(5))
    iid = np.array([x[rng.integers(0, len(x), len(x))].mean()
                    for _ in range(2000)])
    assert mb.std() > iid.std()


def test_holm_rejects_nothing_when_every_p_is_large():
    assert not any(holm({"a": 0.2, "b": 0.3, "c": 0.9}).values())


def test_holm_is_stricter_than_uncorrected_alpha():
    p = {"a": 0.03, "b": 0.04, "c": 0.045}
    out = holm(p)
    assert sum(out.values()) < 3          # all three clear 0.05 uncorrected


def test_holm_rejects_a_clearly_significant_smallest_p():
    assert holm({"a": 1e-6, "b": 0.9})["a"] is True


def test_ci_p_is_small_when_the_ci_excludes_zero():
    assert ci_p(0.10, 0.05, 0.15) < 0.05
    assert ci_p(0.01, -0.10, 0.12) > 0.05


# ── the pre-declared labels ───────────────────────────────────────────────────
def test_label_adds_value_only_when_the_rise_ci_excludes_zero():
    assert label_transition(0, 0, 0.01, 0.05, 5000) == "ADDS VALUE"
    assert label_transition(0, 0, -0.05, -0.01, 5000) == "COSTS"


def test_label_says_shrinks_the_sample_when_the_rise_ci_contains_zero():
    """The default expectation for any gate that selects rarer, larger-R setups —
    and the reason the control exists at all."""
    assert label_transition(0, 0, -0.02, 0.03, 5000) == "MERELY SHRINKS THE SAMPLE"


def test_label_says_underpowered_below_the_power_floor():
    out = label_transition(0, 0, -0.2, 0.3, POWER_FLOOR_5PP - 1)
    assert "INDETERMINATE" in out and "underpowered" in out


def test_verdict_calls_a_well_powered_zero_a_refutation_not_an_absence():
    """§5.2 item 1 and §5.3 item 1 are different claims and must not blur."""
    big = {"n": POWER_FLOOR_5PP + 10, "diff_r_lo": -0.02, "diff_r_hi": 0.02}
    small = {"n": 100, "diff_r_lo": -0.4, "diff_r_hi": 0.4}
    assert "REFUTES" in verdict_for(big)
    assert "INDETERMINATE" in verdict_for(small)


# ── the sanity floor ──────────────────────────────────────────────────────────
def test_sanity_floor_flags_an_impossible_book():
    s = {"win": 0.97, "exp_r": 1.8, "pf": 9.0}
    flags = sanity_flags(s, 0.30)
    assert len(flags) == 4


def test_sanity_floor_is_silent_on_a_plausible_book():
    assert sanity_flags({"win": 0.36, "exp_r": 0.02, "pf": 1.05}, 0.01) == []


# ── regime blocks ─────────────────────────────────────────────────────────────
def test_calendar_blocks_are_four_equal_contiguous_spans():
    m1 = _m1(20000)
    bl = calendar_blocks(m1)
    assert [b[0] for b in bl] == ["B1", "B2", "B3", "B4"]
    assert bl[0][1] == m1.index.min()
    assert bl[-1][2] == m1.index.max()
    widths = [(b[2] - b[1]).total_seconds() for b in bl]
    assert max(widths) - min(widths) < 1.0
    for a, b in zip(bl, bl[1:]):
        assert a[2] == b[1]


# ── the Book, end to end on synthetic data ────────────────────────────────────
def test_book_slices_a_rung_to_exactly_its_own_control(book):
    """Every rung is a subset of R0 and its control is the matched subset. If the
    control arm changed between rungs the ladder's comparisons would not be
    comparable at all."""
    m1, bars, ev, tr = book
    tgt = target_levels(tr, "2R")
    ctrl_tr, ctgt = matched_control(tr, tgt, bars, m1, "15min")
    real = apply_cost(resolve(tr, tgt, m1, tie="stop"), "0.04R")
    ctrl = apply_cost(resolve(ctrl_tr, ctgt, m1, tie="stop"), "0.04R")
    bk = Book(real, ctrl, len(ev), 1.0)
    rng = np.random.default_rng(0)
    mask = rng.random(len(ev)) < 0.4
    c = bk.cell(mask)
    assert c["n"] > 0
    # the control arm is at most reps x the real arm, and never fewer than one
    assert c["n_ctrl"] <= 5 * c["n"]
    assert c["n_ctrl"] > 0
    full = bk.cell(np.ones(len(ev), bool))
    assert full["n"] >= c["n"]


def test_book_expectancy_and_win_rate_agree_with_the_raw_columns(book):
    m1, bars, ev, tr = book
    tgt = target_levels(tr, "2R")
    ctrl_tr, ctgt = matched_control(tr, tgt, bars, m1, "15min")
    real = apply_cost(resolve(tr, tgt, m1, tie="stop"), 0.0)
    ctrl = apply_cost(resolve(ctrl_tr, ctgt, m1, tie="stop"), 0.0)
    bk = Book(real, ctrl, len(ev), 1.0)
    c = bk.cell(np.ones(len(ev), bool))
    assert c["exp_r"] == pytest.approx(real["net_r"].mean())
    assert c["win"] == pytest.approx((real["net_usd"] > 0).mean())
    assert c["diff_r"] == pytest.approx(real["net_r"].mean()
                                        - ctrl["net_r"].mean(), abs=1e-9)
