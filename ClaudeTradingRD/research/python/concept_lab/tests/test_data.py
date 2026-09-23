"""Bars, DST, the 4H grid knob, availability lookups, cache atomicity."""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import concept_lab as cl
from concept_lab import data as D
from concept_lab.sessions import window_hilo

NY = "America/New_York"


def continuous_m1(start, end, seed=0):
    idx = pd.date_range(start, end, freq="1min", tz="UTC", inclusive="left")
    rng = np.random.default_rng(seed)
    c = 2000 + np.cumsum(rng.normal(0, .1, len(idx)))
    o = np.concatenate([[2000], c[:-1]])
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + .05,
                         "low": np.minimum(o, c) - .05, "close": c}, index=idx)


@pytest.fixture(scope="module")
def dst_m1():
    # both 2024 DST switches: 10 March (spring) and 3 November (fall), 24/7 data
    return pd.concat([continuous_m1("2024-03-06", "2024-03-14"),
                      continuous_m1("2024-10-30", "2024-11-07", seed=1)])


@pytest.mark.parametrize("grid,hours", [("forex", {1, 5, 9, 13, 17, 21}),
                                         ("futures", {2, 6, 10, 14, 18, 22})])
def test_4h_grid_on_ny_clock_across_dst(dst_m1, grid, hours):
    b = cl.build_bars(dst_m1, "4h", grid4h=grid)
    ny = b.index.tz_convert(NY)
    # every label is a grid hour on the NEW YORK clock, summer and winter alike —
    # except the futures bar whose nominal open (02:00 on 10 March) does not exist;
    # it is labelled by its first real minute, 03:00 EDT (gold is shut then anyway)
    odd = ny[~np.isin(ny.hour, list(hours))]
    assert len(odd) == (1 if grid == "futures" else 0)
    if len(odd):
        assert odd[0] == pd.Timestamp("2024-03-10 03:00", tz=NY)
    assert set(ny.minute) == {0}
    # so in UTC the same NY bar moves by an hour across the switch
    utc17 = b.index[(ny.hour == (17 if grid == "forex" else 18))]
    summer = utc17[utc17 > pd.Timestamp("2024-03-11", tz="UTC")]
    winter = utc17[utc17 < pd.Timestamp("2024-03-10", tz="UTC")]
    assert set(summer[summer < pd.Timestamp("2024-04-01", tz="UTC")].hour) == \
        {21 if grid == "forex" else 22}
    assert set(winter.hour) == {22 if grid == "forex" else 23}


def test_4h_utc_knob(dst_m1):
    b = cl.build_bars(dst_m1, "4h", grid4h="utc")
    assert set(b.index.hour) <= {0, 4, 8, 12, 16, 20}
    assert ((b["close_time"] - b.index) == pd.Timedelta("4h")).all()


def test_4h_bar_spanning_spring_forward_is_3h(dst_m1):
    b = cl.build_bars(dst_m1, "4h", grid4h="forex")
    ny_open = pd.Timestamp("2024-03-10 01:00", tz=NY)
    row = b.loc[ny_open.tz_convert("UTC")]
    assert row["close_time"] - ny_open.tz_convert("UTC") == pd.Timedelta("3h")
    assert row["n_m1"] == 180


def test_daily_roll_18_ny_with_dst(dst_m1):
    d = cl.build_bars(dst_m1, "1D")
    ny = d.index.tz_convert(NY)
    assert set(ny.hour) == {18} and set(ny.minute) == {0}
    # close_time = the next 18:00 NY
    assert set(pd.DatetimeIndex(d["close_time"]).tz_convert(NY).hour) == {18}
    full = d[(d.index > pd.Timestamp("2024-03-06 23:00", tz="UTC")) &
             (d["close_time"] < pd.Timestamp("2024-03-14", tz="UTC"))]
    lens = (pd.DatetimeIndex(full["close_time"]) - full.index)
    # the day containing the spring-forward switch is 23 hours long, others 24
    assert sorted(set(lens)) == [pd.Timedelta("23h"), pd.Timedelta("24h")]
    assert (full.loc[lens == pd.Timedelta("23h"), "n_m1"] == 23 * 60).all()
    fall = d[(d.index > pd.Timestamp("2024-10-31", tz="UTC")) &
             (d["close_time"] < pd.Timestamp("2024-11-07", tz="UTC"))]
    assert pd.Timedelta("25h") in set(pd.DatetimeIndex(fall["close_time"]) - fall.index)


def test_trading_day_label():
    t = pd.DatetimeIndex([pd.Timestamp("2024-03-11 10:00", tz=NY),     # Monday morning
                          pd.Timestamp("2024-03-11 18:00", tz=NY)])    # Monday 18:00
    td = cl.trading_day(t)
    assert list(td.strftime("%a")) == ["Sun", "Mon"]


def test_bars_close_time_and_intraday_alignment(flat_m1):
    for tf in ("5min", "15min", "1h"):
        b = cl.bars(tf, m1=flat_m1)
        assert ((b["close_time"] - b.index) == pd.Timedelta(tf)).all()
        assert (pd.DatetimeIndex(b["last_m1"]) < pd.DatetimeIndex(b["close_time"])).all()
    # same buckets as the phase-2/3 resampler
    from bars import resample
    ref = resample(flat_m1, "15min")
    b = cl.bars("15min", m1=flat_m1)
    pd.testing.assert_frame_equal(b[["open", "high", "low", "close"]], ref,
                                  check_names=False, check_freq=False, check_index_type=False)


def test_asof_never_returns_bar_in_progress(flat_m1):
    b = cl.bars("1h", m1=flat_m1)
    t = pd.DatetimeIndex([pd.Timestamp("2020-06-03 15:30", tz="UTC"),
                          pd.Timestamp("2020-06-03 15:00", tz="UTC")])
    a = cl.asof(b, t)
    # at 15:30 the 15:00 bar is in progress: the last CLOSED bar is 14:00
    assert a["bar_start"].iloc[0] == pd.Timestamp("2020-06-03 14:00", tz="UTC")
    # at exactly 15:00 the 14:00 bar has just closed and is admissible
    assert a["bar_start"].iloc[1] == pd.Timestamp("2020-06-03 14:00", tz="UTC")
    assert (pd.DatetimeIndex(a["available_at"]) <= t).all()


def test_prior_day_high_is_completed_day(dst_m1):
    t = pd.DatetimeIndex([pd.Timestamp("2024-03-12 10:00", tz=NY)])   # Tuesday 10:00
    p = cl.prior_hilo(t, "1D", m1=dst_m1)
    # completed day = Sunday 18:00 -> Monday 18:00 (label Sunday), NOT the one in progress
    assert p["period_start"].iloc[0] == pd.Timestamp("2024-03-10 18:00", tz=NY)
    assert pd.Timestamp(p["available_at"].iloc[0]) == pd.Timestamp("2024-03-11 18:00", tz=NY)
    d = cl.build_bars(dst_m1, "1D")
    assert p["high"].iloc[0] == d.loc[pd.Timestamp("2024-03-10 18:00", tz=NY), "high"]
    p2 = cl.prior_hilo(t, "1D", n_back=2, m1=dst_m1)
    assert p2["period_start"].iloc[0] == pd.Timestamp("2024-03-09 18:00", tz=NY) or \
        p2["period_start"].iloc[0] < p["period_start"].iloc[0]


def test_session_window_available_at_ny_clock(dst_m1):
    w = window_hilo("ny_am", m1=dst_m1)                           # 08:30-12:00 NY
    av = pd.DatetimeIndex(w["available_at"]).tz_convert(NY)
    assert set(zip(av.hour, av.minute)) == {(12, 0)}
    utc = pd.DatetimeIndex(w["available_at"])
    assert set(utc.hour) == {16, 17}                              # EDT and EST
    t = pd.DatetimeIndex([pd.Timestamp("2024-03-12 11:59", tz=NY),
                          pd.Timestamp("2024-03-12 12:00", tz=NY)])
    p = cl.prior_hilo(t, "ny_am", m1=dst_m1)
    assert p["period_start"].iloc[0] < pd.Timestamp("2024-03-12 08:30", tz=NY)   # yesterday's
    assert p["period_start"].iloc[1] == pd.Timestamp("2024-03-12 08:30", tz=NY)  # today's


def test_asia_window_wraps_midnight(dst_m1):
    w = window_hilo("asia", m1=dst_m1)                            # 20:00-00:00 NY
    assert (w["n_m1"].iloc[1:-1] == 240).all()
    av = pd.DatetimeIndex(w["available_at"]).tz_convert(NY)
    assert set(av.hour) == {0}
    with pytest.raises(ValueError):
        window_hilo(("17:00", "19:00"), m1=dst_m1)               # straddles the 18:00 roll


def test_open_at_and_running_hilo(dst_m1):
    t = pd.DatetimeIndex([pd.Timestamp("2024-03-12 09:00", tz=NY),
                          pd.Timestamp("2024-03-11 23:00", tz=NY)])
    o = cl.open_at(t, "00:00", m1=dst_m1)
    assert o["time"].iloc[0] == pd.Timestamp("2024-03-12 00:00", tz=NY)
    assert np.isnan(o["price"].iloc[1])        # today's midnight open not yet printed
    r = cl.running_hilo(t[:1], "1D", m1=dst_m1)
    m = dst_m1[(dst_m1.index >= pd.Timestamp("2024-03-11 18:00", tz=NY)) &
               (dst_m1.index < pd.Timestamp("2024-03-12 09:00", tz=NY))]
    assert r["high"].iloc[0] == m["high"].max() and r["low"].iloc[0] == m["low"].min()


def test_normalize_tf():
    assert cl.normalize_tf("M15") == "15min" and cl.normalize_tf("15m") == "15min"
    assert cl.normalize_tf("H4") == "4h" and cl.normalize_tf("4H") == "4h"
    assert cl.normalize_tf("D") == "1D" and cl.normalize_tf("1M") == "1M"
    assert cl.normalize_tf("1m") == "1min" and cl.normalize_tf("W") == "1W"


_WRITER = """
import sys; sys.path.insert(0, {py!r})
import numpy as np, pandas as pd
from pathlib import Path
from concept_lab import data as D
df = pd.DataFrame({{"x": np.arange(200_000) * 1.0}})
for _ in range(5):
    D._atomic_write_parquet(df, Path({path!r}))
"""


def test_atomic_cache_write_is_process_safe(tmp_path):
    import subprocess
    import sys
    path = tmp_path / "race.parquet"
    py = str(Path(__file__).resolve().parents[2])
    code = _WRITER.format(py=py, path=str(path))
    procs = [subprocess.Popen([sys.executable, "-c", code]) for _ in range(6)]
    assert all(p.wait(timeout=120) == 0 for p in procs)
    out = pd.read_parquet(path)
    assert len(out) == 200_000 and out["x"].iloc[-1] == 199_999
    assert not [p for p in os.listdir(tmp_path) if p.endswith(".tmp")]
