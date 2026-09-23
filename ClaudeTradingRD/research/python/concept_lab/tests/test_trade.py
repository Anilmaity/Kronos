"""Known-truth books: a PLANTED edge must come back EDGE; a planted anti-edge
NEGATIVE; pure-random signals NULL/UNDERPOWERED — never EDGE — across many seeds."""
import numpy as np
import pandas as pd
import pytest

import concept_lab as cl
from concept_lab.rules import EDGE, NEGATIVE, NULL, UNDERPOWERED
from conftest import make_m1, event_positions, events_at

N_EV = 1600


def _planted(sign_of_edge: float, seed: int = 11, drift=0.006):
    base = make_m1(seed=seed)                      # to find the event grid
    pos = event_positions(base, N_EV, seed=seed)
    dirs = np.random.default_rng(seed).choice([-1, 1], len(pos))
    m1 = make_m1(seed=seed, drift_at=(pos, dirs * sign_of_edge), drift=drift, drift_len=60)
    return m1, events_at(m1, pos, dirs, stop_dist=2.0, rr=1.0)


@pytest.fixture(scope="module")
def planted_pos():
    return _planted(+1)


def test_planted_edge_is_edge(planted_pos):
    m1, ev = planted_pos
    r = cl.trade_test(ev, max_hold="90min", m1=m1)
    assert r["verdict"] == EDGE, (r["verdict_detail"], r["diff"], r["ci_lo"])
    assert r["diff"] > 0.1 and r["ci_lo"] > 0
    assert r["halves"]["H1"]["diff"] > 0 and r["halves"]["H2"]["diff"] > 0
    assert r["n"] >= 1500 and isinstance(r["p"], float) and r["p"] < 1e-6
    # control is matched: same stop and target distance -> same R geometry
    assert abs(r["control"]["exit_mix"]["target"] + r["control"]["exit_mix"]["stop"]
               + r["control"]["exit_mix"]["time"] - 1) < 1e-9


def test_implausibly_large_edge_trips_the_sanity_floor():
    """A +0.4R / +23pp 'edge' is treated as a suspected harness fault (phase-3
    §4.1.3), never reported as a finding."""
    m1, ev = _planted(+1, seed=13, drift=0.02)
    r = cl.trade_test(ev, max_hold="90min", m1=m1, n_boot=500)
    assert r["verdict"] == "UNTESTABLE" and r["sanity_flags"]


def test_planted_edge_against_the_claim_is_negative(planted_pos):
    m1, ev = planted_pos
    r = cl.trade_test(ev, max_hold="90min", m1=m1, claim="-")
    assert r["verdict"] == NEGATIVE


def test_planted_anti_edge_is_negative():
    m1, ev = _planted(-1, seed=12)
    r = cl.trade_test(ev, max_hold="90min", m1=m1)
    assert r["verdict"] == NEGATIVE and r["ci_hi"] < 0


def test_random_signals_never_edge_across_seeds():
    """30 independent random books. The locked rule's false-EDGE rate must be
    small: a one-sided 2.5% tail (same-sign halves barely filter it); expected
    0.75 of 30, allow at most 1."""
    verdicts = []
    for s in range(30):
        m1 = make_m1(seed=100 + s, start="2016-01-04", end="2025-12-31")
        pos = event_positions(m1, N_EV, seed=s)
        dirs = np.random.default_rng(s).choice([-1, 1], len(pos))
        ev = events_at(m1, pos, dirs, stop_dist=2.0, rr=1.0)
        r = cl.trade_test(ev, max_hold="90min", m1=m1, n_boot=1000, blocks=False)
        verdicts.append(r["verdict"])
    counts = pd.Series(verdicts).value_counts().to_dict()
    assert counts.get(EDGE, 0) <= 1, counts
    assert counts.get(NEGATIVE, 0) <= 3, counts
    assert counts.get(NULL, 0) + counts.get(UNDERPOWERED, 0) >= 26, counts


def test_random_small_book_is_underpowered(flat_m1):
    pos = event_positions(flat_m1, 120, seed=5)
    ev = events_at(flat_m1, pos, 1)
    r = cl.trade_test(ev, max_hold="90min", m1=flat_m1)
    assert r["verdict"] in (UNDERPOWERED, NEGATIVE)
    assert r["mde"] > 0.1 and r["power_floor_n"] > r["n"]


def test_cost_cancels_in_differential_but_not_in_avg_R(planted_pos):
    m1, ev = planted_pos
    a = cl.trade_test(ev, max_hold="90min", m1=m1, cost=0.0, n_boot=200, blocks=False)
    b = cl.trade_test(ev, max_hold="90min", m1=m1, cost="0.1R", n_boot=200, blocks=False)
    assert abs(a["diff"] - b["diff"]) < 1e-12
    assert abs((a["avg_R"] - b["avg_R"]) - 0.1) < 1e-9
    assert abs(b["avg_R_gross"] - a["avg_R"]) < 1e-9


def test_drops_are_counted_not_silent(flat_m1):
    pos = event_positions(flat_m1, 50, seed=6)
    t = flat_m1.index[pos]
    ev = pd.DataFrame({"decision_time": t, "available_at": t, "direction": 1,
                       "stop_px": flat_m1["open"].iloc[pos].to_numpy() + 5,   # above a long
                       "rr": 2.0})
    r = cl.trade_test(ev, max_hold="1h", m1=flat_m1)
    assert r["dropped"]["stop_not_beyond_entry"] == 50 and r["n"] == 0


def test_max_hold_is_required(flat_m1):
    pos = event_positions(flat_m1, 50, seed=7)
    with pytest.raises(ValueError):
        cl.trade_test(events_at(flat_m1, pos, 1), m1=flat_m1)


def test_threshold_cannot_be_loosened(flat_m1):
    pos = event_positions(flat_m1, 50, seed=8)
    with pytest.raises(ValueError):
        cl.trade_test(events_at(flat_m1, pos, 1), max_hold="1h", m1=flat_m1,
                      mde_threshold=0.5)


def test_hold_basis_bars_equalises_exposure_across_the_weekend(flat_m1):
    """Friday 16:30 UTC decisions (the synthetic venue shuts at 17:00): a 2h
    wall-clock hold holds only 30 tradable bars; hold_basis='bars' gives 120,
    for the real trade and its control alike."""
    t = flat_m1.index
    pos = np.flatnonzero((t.dayofweek == 4) & (t.hour == 16) & (t.minute == 30))[:300]
    ev = events_at(flat_m1, pos, 1, stop_dist=50.0, rr=10.0)      # time exits only
    clock = cl.trade_test(ev, max_hold="2h", m1=flat_m1, n_boot=200, blocks=False)
    bars = cl.trade_test(ev, max_hold="2h", m1=flat_m1, n_boot=200, blocks=False,
                         hold_basis="bars")
    assert clock["exposure_bars"]["real_mean"] == 30
    assert clock["exposure_bars"]["control_mean"] > 60              # the mismatch, visible
    assert bars["exposure_bars"]["real_mean"] == 120
    assert bars["exposure_bars"]["control_mean"] == 120
