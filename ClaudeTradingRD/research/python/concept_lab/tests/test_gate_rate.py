"""gate_test and rate_test on known truth."""
import numpy as np
import pandas as pd
import pytest

import concept_lab as cl
from concept_lab.rules import EDGE, NEGATIVE, NULL, UNDERPOWERED
from conftest import make_m1, event_positions, events_at


@pytest.fixture(scope="module")
def half_planted():
    """4,000 random-direction events; ONLY the odd-numbered ones carry a planted
    edge. A gate selecting them must be EDGE; a random gate must not."""
    seed = 21
    base = make_m1(seed=seed)
    pos = event_positions(base, 4000, seed=seed, utc_hour=(14, 15))
    dirs = np.random.default_rng(seed).choice([-1, 1], len(pos))
    good = np.arange(len(pos)) % 2 == 1
    m1 = make_m1(seed=seed, drift_at=(pos[good], dirs[good]), drift=0.008, drift_len=60)
    return m1, events_at(m1, pos, dirs, stop_dist=2.0, rr=1.0), good


def test_gate_selecting_the_edge_is_edge(half_planted):
    m1, ev, good = half_planted
    r = cl.gate_test(ev, good, mask_available_at=ev["decision_time"], max_hold="90min",
                     m1=m1)
    assert r["verdict"] == EDGE, r["verdict_detail"]
    assert r["gate_firing_rate"] == pytest.approx(0.5)
    assert r["gated_vs_own_control"]["ci_lo"] > 0
    assert abs(r["complement"]["vs_own_control"]["diff"]) < 0.06


def test_gate_claim_minus_on_good_gate_is_negative(half_planted):
    m1, ev, good = half_planted
    r = cl.gate_test(ev, good, mask_available_at=ev["decision_time"], max_hold="90min",
                     m1=m1, claim="-", n_boot=500, blocks=False)
    assert r["verdict"] == NEGATIVE


def test_random_gate_is_not_edge(half_planted):
    m1, ev, good = half_planted
    hits = []
    for s in range(8):
        mask = np.random.default_rng(s).random(len(ev)) < 0.5
        r = cl.gate_test(ev, mask, mask_available_at=ev["decision_time"],
                         max_hold="90min", m1=m1, n_boot=500, blocks=False)
        hits.append(r["verdict"])
    assert hits.count(EDGE) == 0, hits


def test_rate_planted_lift_is_edge_and_null_is_null(flat_m1):
    t = flat_m1.index[event_positions(flat_m1, 2500, seed=4)]
    rng = np.random.default_rng(0)
    p = np.full(len(t), 0.4)
    r = cl.rate_test(rng.random(len(t)) < 0.5, t, available_at=t, null_p=p, m1=flat_m1)
    assert r["verdict"] == EDGE and r["lift"] > 1.15
    r0 = cl.rate_test(rng.random(len(t)) < 0.4, t, available_at=t, null_p=p, m1=flat_m1)
    assert r0["verdict"] in (NULL, UNDERPOWERED) and r0["verdict"] != EDGE


def test_rate_with_null_fn_on_matched_random_times(flat_m1):
    """'Price revisits a level 1.0 above within 60 min' — a pure-geometry claim.
    Under the null (same geometry at matched random moments) the hit rate is the
    same, so the verdict must not be EDGE."""
    t = flat_m1.index[event_positions(flat_m1, 2000, seed=9)]
    px = flat_m1["open"].reindex(t).to_numpy()
    obs = cl.touch(t, px + 1.0, "above", "60min", m1=flat_m1)["hit"].to_numpy()
    rt = cl.sample_times(t, 5, 30, seed=3, m1=flat_m1)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        okk = ~tk.isna()
        out = np.full(len(t), np.nan)
        pk = flat_m1["open"].reindex(tk[okk]).to_numpy()
        out[okk] = cl.touch(tk[okk], pk + 1.0, "above", "60min", m1=flat_m1)["hit"]
        return out
    r = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, m1=flat_m1)
    assert r["verdict"] != EDGE
    assert abs(r["diff"]) < 0.05 and r["control"]["reps"] == 5
