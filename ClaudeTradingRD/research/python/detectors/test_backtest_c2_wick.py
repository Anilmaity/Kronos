"""Tests for the C2 wick backtest.

The point of these is not that the numbers are pretty — it is that the
conservative conventions the backtest claims in its docstring are actually the
ones the code implements. A backtest that silently resolves same-bar ambiguity
in the trade's favour would report a fictional edge, and no amount of careful
prose in the report would catch it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest_c2_wick import (  # noqa: E402
    apply_cost, baseline_trades, boot_diff, build_trades, bucketise,
    matched_control, mde, n_for_effect, perm_p, quintile_edges, resolve, stats,
    target_levels, truncate_at_gap,
)


def m1_from(rows, start="2024-01-01 00:00", freq="1min"):
    idx = pd.date_range(start, periods=len(rows), freq=freq, tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def one_trade(entry, stop, long_=True, i0=0, i1=10, risk=None):
    return pd.DataFrame([{
        "time": pd.Timestamp("2024-01-01", tz="UTC"), "tf": "1h", "long": long_,
        "entry": entry, "stop": stop,
        "risk": abs(entry - stop) if risk is None else risk,
        "struct_target": np.nan, "wick_ratio": 0.3, "body_ratio": 0.3,
        "i0": i0, "i1": i1, "j0": i0, "j1": i1,
    }])


# ── resolution conventions ────────────────────────────────────────────────────
def test_same_bar_stop_and_target_resolves_to_the_stop():
    """The single most important convention: M1 gives no intrabar order."""
    m1 = m1_from([(100, 112, 88, 100)] * 3)      # one bar spans both levels
    tr = one_trade(entry=100, stop=90, i0=0, i1=3)
    r = resolve(tr, np.array([110.0]), m1)
    assert r.iloc[0]["reason"] == "stop"
    assert r.iloc[0]["gross_usd"] == pytest.approx(-10.0)


def test_target_alone_is_taken():
    m1 = m1_from([(100, 111, 99, 110)] * 2)
    r = resolve(one_trade(100, 90, i0=0, i1=2), np.array([110.0]), m1)
    assert r.iloc[0]["reason"] == "target"
    assert r.iloc[0]["gross_usd"] == pytest.approx(10.0)


def test_earlier_stop_beats_later_target():
    m1 = m1_from([(100, 101, 89, 95), (95, 115, 94, 114)])
    r = resolve(one_trade(100, 90, i0=0, i1=2), np.array([110.0]), m1)
    assert r.iloc[0]["reason"] == "stop"


def test_earlier_target_beats_later_stop():
    m1 = m1_from([(100, 111, 99, 110), (110, 111, 85, 88)])
    r = resolve(one_trade(100, 90, i0=0, i1=2), np.array([110.0]), m1)
    assert r.iloc[0]["reason"] == "target"


def test_gap_through_the_stop_fills_at_the_open_not_the_level():
    """Gap risk is paid. Filling at the stop level would invent money."""
    m1 = m1_from([(85, 86, 84, 85)])             # opens 5 below the 90 stop
    r = resolve(one_trade(100, 90, i0=0, i1=1), np.array([110.0]), m1)
    assert r.iloc[0]["reason"] == "stop"
    assert r.iloc[0]["exit_px"] == pytest.approx(85.0)


def test_gap_through_the_target_still_fills_at_the_level():
    """The mirror case is deliberately NOT credited: asymmetry favours the null."""
    m1 = m1_from([(120, 121, 119, 120)])
    r = resolve(one_trade(100, 90, i0=0, i1=1), np.array([110.0]), m1)
    assert r.iloc[0]["exit_px"] == pytest.approx(110.0)


def test_time_exit_uses_the_last_close_in_the_window():
    m1 = m1_from([(100, 101, 99, 100), (100, 102, 99, 101.5), (101, 130, 70, 101)])
    r = resolve(one_trade(100, 90, i0=0, i1=2), np.array([110.0]), m1)
    assert r.iloc[0]["reason"] == "time"
    assert r.iloc[0]["exit_px"] == pytest.approx(101.5)
    assert r.iloc[0]["gross_usd"] == pytest.approx(1.5)


def test_short_side_is_mirrored():
    m1 = m1_from([(100, 101, 89, 90)])
    r = resolve(one_trade(100, 110, long_=False, i0=0, i1=1), np.array([90.0]), m1)
    assert r.iloc[0]["reason"] == "target"
    assert r.iloc[0]["gross_usd"] == pytest.approx(10.0)


def test_trade_with_no_expressible_target_is_dropped_not_zeroed():
    m1 = m1_from([(100, 101, 99, 100)])
    r = resolve(one_trade(100, 90, i0=0, i1=1), np.array([np.nan]), m1)
    assert r.empty


# ── targets ───────────────────────────────────────────────────────────────────
def test_r_multiple_targets():
    tr = one_trade(entry=100, stop=90)
    assert target_levels(tr, "1R")[0] == pytest.approx(110.0)
    assert target_levels(tr, "3R")[0] == pytest.approx(130.0)
    short = one_trade(entry=100, stop=110, long_=False)
    assert target_levels(short, "2R")[0] == pytest.approx(80.0)


def test_structural_target_behind_the_entry_is_nan_not_clipped():
    tr = one_trade(entry=100, stop=90)
    tr["struct_target"] = 95.0            # already below a long entry
    assert np.isnan(target_levels(tr, "structural")[0])
    tr["struct_target"] = 105.0
    assert target_levels(tr, "structural")[0] == pytest.approx(105.0)


# ── costs ─────────────────────────────────────────────────────────────────────
def test_flat_and_proportional_costs():
    r = pd.DataFrame({"gross_usd": [10.0], "risk": [5.0]})
    assert apply_cost(r, 0.2).iloc[0]["net_usd"] == pytest.approx(9.8)
    assert apply_cost(r, 0.2).iloc[0]["net_r"] == pytest.approx(9.8 / 5)
    # 0.04R of a 5 USD risk is 0.20 USD -- same answer, by construction
    assert apply_cost(r, "0.04R").iloc[0]["net_usd"] == pytest.approx(9.8)
    # ...but on a 15 USD risk the proportional cost is three times as large
    r2 = pd.DataFrame({"gross_usd": [10.0], "risk": [15.0]})
    assert apply_cost(r2, "0.04R").iloc[0]["net_usd"] == pytest.approx(9.4)


# ── metrics ───────────────────────────────────────────────────────────────────
def test_stats_on_a_known_book():
    res = pd.DataFrame({
        "net_usd": [2.0, -1.0, 2.0, -1.0],
        "net_r": [2.0, -1.0, 2.0, -1.0],
        "risk": [1.0] * 4,
        "reason": ["target", "stop", "target", "time"],
        "exit_time": pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC"),
    })
    s = stats(res)
    assert s["n"] == 4
    assert s["win"] == pytest.approx(0.5)
    assert s["exp_r"] == pytest.approx(0.5)
    assert s["pf"] == pytest.approx(2.0)
    assert s["mdd_r"] == pytest.approx(1.0)      # 2 -> 1 after the first loser
    assert s["time_exit"] == pytest.approx(0.25)


def test_stats_empty_is_safe():
    assert stats(pd.DataFrame(columns=["net_usd", "net_r", "risk", "reason",
                                       "exit_time"]))["n"] == 0


# ── bucketing ─────────────────────────────────────────────────────────────────
def test_quintile_edges_and_bucketise():
    w = np.arange(100, dtype=float) / 100
    e = quintile_edges(w)
    assert len(e) == 4
    b = bucketise(w, e)
    assert b.min() == 0 and b.max() == 4
    assert np.bincount(b).min() >= 15          # roughly even fifths


def test_edges_fitted_on_one_sample_apply_unchanged_to_another():
    """Holdout bucketing must not see the holdout's own distribution."""
    fit = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    e = quintile_edges(fit)
    held = np.array([0.05, 0.95])
    assert list(bucketise(held, e)) == [0, 4]


# ── permutation test ──────────────────────────────────────────────────────────
def test_permutation_p_is_large_when_groups_are_identical():
    rng = np.random.default_rng(0)
    a, b = rng.normal(size=800), rng.normal(size=800)
    _, p, _ = perm_p(a, b, n_perm=500)
    assert p > 0.05


def test_permutation_p_is_small_when_the_gap_is_real():
    rng = np.random.default_rng(1)
    a, b = rng.normal(1.0, 1.0, 800), rng.normal(0.0, 1.0, 800)
    d, p, ci = perm_p(a, b, n_perm=500)
    assert d > 0.5 and p < 0.01
    assert ci[0] > 0


def test_permutation_p_on_degenerate_groups_is_nan():
    d, p, ci = perm_p(np.array([1.0]), np.array([0.0]), n_perm=10)
    assert np.isnan(p)


# ── the two controls ──────────────────────────────────────────────────────────
def test_optimistic_tie_break_flips_the_same_bar_case():
    """6c leans on this: the only difference between the columns is the guess."""
    m1 = m1_from([(100, 112, 88, 100)] * 3)
    tr = one_trade(entry=100, stop=90, i0=0, i1=3)
    assert resolve(tr, np.array([110.0]), m1).iloc[0]["reason"] == "stop"
    opt = resolve(tr, np.array([110.0]), m1, tie="target")
    assert opt.iloc[0]["reason"] == "target"
    assert opt.iloc[0]["gross_usd"] == pytest.approx(10.0)


def test_bad_tie_break_rejected():
    with pytest.raises(ValueError):
        resolve(one_trade(100, 90), np.array([110.0]),
                m1_from([(100, 101, 99, 100)]), tie="coinflip")


def test_boot_diff_brackets_a_known_gap():
    rng = np.random.default_rng(3)
    a, b = rng.normal(1.0, 1.0, 500), rng.normal(0.0, 1.0, 500)
    d, lo, hi = boot_diff(a, b, n=300)
    assert lo < d < hi
    assert lo > 0                       # a real gap: CI clears zero


def test_boot_diff_on_identical_groups_straddles_zero():
    rng = np.random.default_rng(4)
    a, b = rng.normal(size=500), rng.normal(size=500)
    _, lo, hi = boot_diff(a, b, n=300)
    assert lo < 0 < hi


# ── power ─────────────────────────────────────────────────────────────────────
def test_mde_shrinks_with_sample_size():
    assert mde(50, 50, 0.4) > mde(500, 500, 0.4) > mde(5000, 5000, 0.4)


def test_mde_and_n_for_effect_are_consistent():
    """n_for_effect(e) trades should have minimum detectable effect ~= e."""
    n = n_for_effect(0.04, 0.4)
    assert mde(int(n // 2), int(n // 2), 0.4) == pytest.approx(0.04, rel=0.02)


def test_a_daily_sample_cannot_see_a_small_effect():
    """The load-bearing power claim: 3 years of 1D C2s is far too few."""
    assert mde(128, 129, 0.40) > 0.10       # ~257 daily C2s over 3 years


# ── session-break handling ────────────────────────────────────────────────────
def test_truncate_at_gap_stops_the_window_at_a_break():
    idx = list(pd.date_range("2024-01-05 20:00", periods=4, freq="1min", tz="UTC"))
    idx += list(pd.date_range("2024-01-07 22:00", periods=4, freq="1min", tz="UTC"))
    m1 = pd.DataFrame([(1, 1, 1, 1)] * 8, columns=["open", "high", "low", "close"],
                      index=pd.DatetimeIndex(idx))
    tr = pd.DataFrame({"i0": [0], "i1": [8]})
    assert truncate_at_gap(tr, m1)[0] == 4, "window must end at the weekend hole"


def test_truncate_at_gap_leaves_contiguous_windows_alone():
    m1 = m1_from([(1, 1, 1, 1)] * 10)
    tr = pd.DataFrame({"i0": [0], "i1": [10]})
    assert truncate_at_gap(tr, m1)[0] == 10


# ── against real data ─────────────────────────────────────────────────────────
PARQUET = Path(__file__).resolve().parents[3] / "m3_scalper" / "xau_m1_3y.parquet"


@pytest.mark.skipif(not PARQUET.exists(), reason="XAUUSD parquet not available")
def test_build_trades_has_no_lookahead_and_sane_geometry():
    from bars import load_m1

    m1 = load_m1()
    tr = build_trades(m1, "4h")
    assert len(tr) > 100
    # the resolution window must start strictly after the signal bar closes
    starts = m1.index[tr["i0"].to_numpy()]
    assert (starts >= tr["time"] + pd.Timedelta("4h")).all()
    # stop is on the losing side of the entry, always
    long_ = tr["long"].to_numpy()
    assert (tr["stop"].to_numpy()[long_] < tr["entry"].to_numpy()[long_]).all()
    assert (tr["stop"].to_numpy()[~long_] > tr["entry"].to_numpy()[~long_]).all()
    assert (tr["risk"] > 0).all()


@pytest.mark.skipif(not PARQUET.exists(), reason="XAUUSD parquet not available")
def test_wick_ratio_is_the_opposing_run_over_range():
    """The fitted cuts define the numerator as open -> extreme, one-sided.

    If this identity ever breaks, the thresholds imported from
    `meta/threshold_fits.md` stop meaning what that document says they mean.
    """
    from bars import load_m1, resample
    from detectors.fractal import c2_events

    ev = c2_events(resample(load_m1(), "1h"))
    o, h, lo_ = ev["open"], ev["high"], ev["low"]
    opp = np.where(ev["direction"] == "bullish", o - lo_, h - o)
    assert np.allclose(opp / (h - lo_), ev["wick_ratio"])

    # the body form is the same numerator over |close - open|
    want = pd.Series((opp / np.abs(ev["close"] - ev["open"])).to_numpy(),
                     index=pd.DatetimeIndex(ev["time"]))
    tr = build_trades(load_m1(), "1h").set_index("time")
    got, exp = tr["wick_body"], want.reindex(tr.index)
    ok = np.isfinite(got) & np.isfinite(exp)
    assert ok.sum() > 1000
    assert np.allclose(got[ok], exp[ok])


@pytest.mark.skipif(not PARQUET.exists(), reason="XAUUSD parquet not available")
def test_a_1r_book_cannot_win_more_than_it_should():
    """Sanity ceiling: at 1R with a stop-first tie-break, wins are bounded."""
    from bars import load_m1

    m1 = load_m1()
    tr = build_trades(m1, "4h")
    r = apply_cost(resolve(tr, target_levels(tr, "1R"), m1), 0.0)
    assert 0.30 < (r["reason"] == "target").mean() < 0.70
    assert r["gross_usd"].max() <= r["risk"].max() * 1.01


@pytest.mark.skipif(not PARQUET.exists(), reason="XAUUSD parquet not available")
def test_matched_control_matches_the_geometry_it_claims_to():
    """If the control is not geometrically identical it is not a control."""
    from bars import load_m1, resample

    m1 = load_m1()
    df = resample(m1, "4h")
    tr = build_trades(m1, "4h")
    lv = target_levels(tr, "2R")
    ctr, ctgt = matched_control(tr, lv, df, m1, "4h", reps=2)

    reps = 2
    src = tr[np.isfinite(lv)].reset_index(drop=True)
    assert len(ctr) <= reps * len(src)
    # same direction mix, same stop distance, same target distance
    assert ctr["long"].mean() == pytest.approx(src["long"].mean(), abs=0.02)
    assert np.allclose(np.abs(ctr["entry"] - ctr["stop"]), ctr["risk"])
    assert np.allclose(np.abs(ctgt - ctr["entry"].to_numpy()),
                       2.0 * ctr["risk"].to_numpy())
    # ...but a different entry time, which is the whole point
    assert (ctr["time"].to_numpy()[:len(src)] != src["time"].to_numpy()).mean() > 0.9


@pytest.mark.skipif(not PARQUET.exists(), reason="XAUUSD parquet not available")
def test_coarse_resolution_wins_more_than_m1_under_an_optimistic_tie_break():
    """The artefact 6c reports must exist and point the direction it claims."""
    from bars import load_m1, resample

    m1 = load_m1()
    df = resample(m1, "4h")
    tr = build_trades(m1, "4h")
    lv = target_levels(tr, "2R")
    fine = resolve(tr, lv, m1)
    opt = resolve(tr, lv, df, "j0", "j1", tie="target")
    assert (opt["reason"] == "target").mean() > (fine["reason"] == "target").mean()


@pytest.mark.skipif(not PARQUET.exists(), reason="XAUUSD parquet not available")
def test_baseline_covers_every_bar_in_both_directions():
    from bars import load_m1
    from bars import resample

    m1 = load_m1()
    bt = baseline_trades(m1, "1D")
    assert bt["long"].sum() > 0 and (~bt["long"]).sum() > 0
    assert len(bt) > len(build_trades(m1, "1D"))
    assert len(bt) <= 2 * len(resample(m1, "1D"))
