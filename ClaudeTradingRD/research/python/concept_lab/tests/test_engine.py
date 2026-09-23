"""The vectorised M1 resolver must equal the phase-2/3 reference resolver exactly,
and keep its conservative conventions (stop-first ties, gap-through-stop fills)."""
import numpy as np
import pandas as pd
import pytest

from backtest_c2_wick import resolve as ref_resolve
from concept_lab.engine import Market, resolve_trades, sample_times, touch, _first_ge
from conftest import make_m1


@pytest.fixture(scope="module")
def small_m1():
    return make_m1(start="2020-01-06", end="2020-03-31", utc_hours=(0, 24), seed=3,
                   vol=0.3)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_resolver_matches_reference_exactly(small_m1, seed):
    mkt = Market(small_m1)
    rng = np.random.default_rng(seed)
    n = 3000
    N = len(small_m1)
    i0 = rng.integers(0, N - 3000, n)
    hold = rng.choice([1, 5, 63, 64, 65, 200, 700, 2000], n)       # straddle block edges
    i1 = np.minimum(i0 + hold, N)
    long_ = rng.random(n) < 0.5
    entry = mkt.o[i0]
    risk = rng.uniform(0.2, 4.0, n)
    sg = np.where(long_, 1, -1)
    stop = entry - sg * risk
    tgt = entry + sg * risk * rng.choice([0.5, 1, 2, 3], n)
    tr = pd.DataFrame({"long": long_, "stop": stop, "entry": entry, "i0": i0, "i1": i1})
    ref = ref_resolve(tr, tgt, small_m1, tie="stop")
    got = resolve_trades(mkt, long_, stop, tgt, i0, i1)
    assert len(ref) == n
    np.testing.assert_array_equal(got["exit_px"], ref["exit_px"].to_numpy())
    code = {"stop": 0, "target": 1, "time": 2}
    np.testing.assert_array_equal(got["reason"], ref["reason"].map(code).to_numpy())
    np.testing.assert_array_equal(small_m1.index[got["exit_pos"]], ref["exit_time"])


def _bars(rows, start="2021-02-01 10:00"):
    idx = pd.date_range(start, periods=len(rows), freq="1min", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def test_same_bar_stop_and_target_resolves_as_stop():
    m1 = _bars([[100, 100.5, 99.5, 100], [100, 103, 97, 100], [100, 104, 99.9, 103]])
    mkt = Market(m1)
    r = resolve_trades(mkt, [True], [98.0], [102.0], [0], [3])
    assert r["reason"][0] == 0 and r["exit_px"][0] == 98.0 and r["exit_pos"][0] == 1


def test_gap_through_stop_fills_at_open():
    m1 = _bars([[100, 100.5, 99.5, 100], [96, 96.5, 95, 96], [96, 97, 95.5, 96]])
    r = resolve_trades(Market(m1), [True], [98.0], [102.0], [0], [3])
    assert r["reason"][0] == 0 and r["exit_px"][0] == 96.0      # the gap is paid


def test_time_exit_and_no_target():
    m1 = _bars([[100, 100.5, 99.5, 100.2], [100.2, 100.6, 99.8, 100.4]])
    r = resolve_trades(Market(m1), [False], [105.0], [np.nan], [0], [2])
    assert r["reason"][0] == 2 and r["exit_px"][0] == 100.4


def test_first_ge_bruteforce(small_m1):
    mkt = Market(small_m1)
    rng = np.random.default_rng(9)
    n = 4000
    i0 = rng.integers(0, len(small_m1) - 5000, n)
    i1 = i0 + rng.integers(0, 5000, n)
    thr = mkt.h[i0] + rng.uniform(-1, 6, n)
    got = _first_ge(mkt.h, mkt.hb, i0, i1, thr)
    for k in range(0, n, 37):
        w = np.flatnonzero(mkt.h[i0[k]:i1[k]] >= thr[k])
        assert got[k] == (i0[k] + w[0] if len(w) else -1)


def test_sample_times_window_grid_and_tod(flat_m1):
    t = flat_m1.index[flat_m1.index.minute == 0][5000:5400:7]
    s = sample_times(t, 5, 30, seed=1, m1=flat_m1)
    ss = pd.DatetimeIndex(s.reshape(-1)).tz_localize("UTC")
    assert not ss.isna().any()
    assert set(ss.minute) == {0}                                  # auto grid = :00
    d = (s - t.tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy()[:, None])
    assert (np.abs(d) <= np.timedelta64(30, "D")).all()
    s2 = sample_times(t, 5, 30, seed=1, m1=flat_m1, align=1, tod_tol_min=0)
    ss2 = pd.DatetimeIndex(s2.reshape(-1)).tz_localize("UTC")
    ok = ~ss2.isna()
    assert ok.mean() > 0.95
    ny = ss2[ok].tz_convert("America/New_York")
    tt = np.repeat(t.tz_convert("America/New_York").hour.to_numpy(), 5)[ok]
    assert (ny.hour.to_numpy() == tt).all() and set(ny.minute) == {0}   # same NY clock


def test_touch(small_m1):
    t = small_m1.index[[100, 5000]]
    lv = small_m1["high"].iloc[[101, 5001]].to_numpy()
    out = touch(t, lv, "above", "10min", m1=small_m1)
    assert out["hit"].all()
    assert (pd.DatetimeIndex(out["hit_time"]) <= small_m1.index[[101, 5001]]).all()
    far = touch(t, lv + 1e6, "above", "10min", m1=small_m1)
    assert not far["hit"].any()
