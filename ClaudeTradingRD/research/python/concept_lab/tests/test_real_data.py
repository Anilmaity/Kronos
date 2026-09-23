"""On the certified XAUUSD span (skipped if the parquet is absent)."""
import numpy as np
import pandas as pd
import pytest

import concept_lab as cl
from concept_lab.rules import EDGE
from conftest import needs_real

pytestmark = needs_real


def test_certified_span():
    m1 = cl.load_m1()
    assert m1.index.min() >= pd.Timestamp("2016-01-01", tz="UTC")     # pre-2016 disqualified
    assert len(m1) > 3_600_000 and m1.index.is_monotonic_increasing


def test_bars_cache_roundtrip():
    from concept_lab import data as D
    b = cl.bars("4h")
    ref = D._build_bars(cl.load_m1(), "4h")
    pd.testing.assert_frame_equal(b, ref, check_freq=False)
    assert list(D.CACHE_DIR.glob("bars_4h_forex_18_*.parquet"))
    assert set(b.index.tz_convert("America/New_York").hour) <= {1, 5, 9, 13, 17, 21, 18, 2}


def test_calibration_rung0_1h_reproduces_phase3():
    from concept_lab.calibrate import run
    rep = run(["R0_1h"])["results"]["R0_1h"]
    import os
    assert "CONCEPT_LAB_LEDGER_DISABLE" not in os.environ     # scoped to the run only
    assert rep["faithful"]["PASS"], rep
    assert rep["faithful"]["n"] == 7995


def test_random_real_entries_are_calibrated_null():
    """Random entries on real gold — half the books ALL-LONG in a bull market — must
    not read as edges: the matched control shares direction, so drift cancels.

    Measured on 80 books while building the harness: z = diff/SE had mean -0.01,
    sd 1.02; 3/80 EDGE and 2/80 NEGATIVE — the ~2.5% one-sided tail the locked rule
    implies (the split-half filter removes almost nothing; review 2026-09-23). So
    this is a CALIBRATION test over 32 books, not a single-seed test (any single seed
    is a ~2.5% coin)."""
    b = cl.bars("1h")
    zs, verdicts = [], []
    for all_long in (True, False):
        for seed in range(16):
            rng = np.random.default_rng(seed)
            pick = np.sort(rng.choice(len(b) - 20, 3000, replace=False))
            t = pd.DatetimeIndex(b["close_time"].iloc[pick])
            px = b["close"].iloc[pick].to_numpy()
            d = np.ones(3000, int) if all_long else rng.choice([-1, 1], 3000)
            ev = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                               "stop_dist": px * 0.003, "rr": 2.0})
            r = cl.trade_test(ev, max_hold="10h", n_boot=1000, blocks=False)
            zs.append(r["diff"] / ((r["ci_hi"] - r["ci_lo"]) / 3.92))
            verdicts.append(r["verdict"])
    zs = np.array(zs)
    assert verdicts.count(EDGE) <= 2, verdicts
    assert abs(zs.mean()) < 0.4 and 0.6 < zs.std() < 1.5, (zs.mean(), zs.std())


def _cisd_1h(m1):
    from detectors.cisd import cisd_events
    b = cl.build_bars(m1, "1h")
    ev = cisd_events(b[["open", "high", "low", "close"]], max_wait=3)
    if ev.empty:
        return pd.DataFrame(columns=["decision_time", "direction"])
    ct = b.loc[ev["confirm_time"], "close_time"].to_numpy()
    return pd.DataFrame({"decision_time": pd.DatetimeIndex(ct),
                         "direction": np.where(ev["direction"] == "bullish", 1, -1)})


def test_probe_lookahead_on_real_cisd_detector():
    m1 = cl.load_m1()
    sl = m1[(m1.index >= "2024-01-01") & (m1.index < "2024-03-01")]
    ev = _cisd_1h(sl)
    ev = ev[ev["decision_time"] > pd.Timestamp("2024-01-20", tz="UTC")]
    out = cl.probe_lookahead(_cisd_1h, ev, m1=m1, n_sample=12, lookback="10D")
    assert out["passed"]


def test_prior_levels_are_always_available():
    rng = np.random.default_rng(0)
    m1 = cl.load_m1()
    t = m1.index[rng.choice(len(m1), 2000, replace=False)]
    for kind in ("1D", "1W", "4h", "ny_am", "fx_london"):
        p = cl.prior_hilo(t, kind)
        ok = p["available_at"].notna()
        assert (pd.DatetimeIndex(p.loc[ok, "available_at"]) <= t[ok.to_numpy()]).all(), kind
