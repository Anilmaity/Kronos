"""Regression tests for the 2026-09-23 two-lens review (lookahead + statistics).

Each test pins one fix; the finding it guards is named in the docstring.
"""
import json
import os

import numpy as np
import pandas as pd
import pytest

import concept_lab as cl
from concept_lab import LookaheadError
from concept_lab import rules as rules_mod
from concept_lab.rules import EDGE, NEGATIVE, NULL, UNDERPOWERED, UNTESTABLE
from conftest import make_m1, event_positions, events_at, needs_real

OP = {"rules": ["synthetic"], "params": {"rr": 1.0}}
SRC = {"rr": "declared-before-run: 1R"}


# ══ synthetic detectors (flat_m1 trades 13:00-17:00 UTC on weekdays) ══════════
def _first15_of_hour(m1, leak: bool):
    """Long at the close of the first 15m bar of each 1h bar when that 15m bar
    closed up; the LEAKY version also requires the enclosing 1h bar — still in
    progress at the decision — to close up (a future FILTER)."""
    b15 = cl.build_bars(m1, "15min")
    b1 = cl.build_bars(m1, "1h")
    pos = np.searchsorted(b1.index.asi8, b15.index.asi8, side="right") - 1
    h1 = b1.iloc[np.clip(pos, 0, None)]
    first = (pos >= 0) & (h1.index.asi8 == b15.index.asi8)
    up15 = (b15["close"] > b15["open"]).to_numpy()
    sel = first & up15
    if leak:
        sel &= h1["close"].to_numpy() > h1["open"].to_numpy()
    ct = pd.DatetimeIndex(b15["close_time"])[sel]
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 1,
                         "stop_dist": 1.0, "rr": 1.0})


def _future_stop(m1):
    """Honest timing, but the stop is the low of the NEXT two 1h bars."""
    b = cl.build_bars(m1, "1h")
    fut = pd.concat([b["low"].shift(-1), b["low"].shift(-2)], axis=1).min(axis=1)
    sel = (b["close"] > b["open"]).to_numpy()
    ct = pd.DatetimeIndex(b["close_time"])[sel]
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 1,
                         "stop_px": np.minimum(b["close"] - 1.0, fut - 0.05).to_numpy()[sel],
                         "rr": 1.0})


def _gate_inprogress(m1):
    """Every 15m close; gate column = 'the enclosing 1h bar closes up' (in progress)."""
    b15 = cl.build_bars(m1, "15min")
    b1 = cl.build_bars(m1, "1h")
    pos = np.searchsorted(b1.index.asi8, b15.index.asi8, side="right") - 1
    h1 = b1.iloc[np.clip(pos, 0, None)]
    ok = pos >= 0
    ct = pd.DatetimeIndex(b15["close_time"])[ok]
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 1,
                         "stop_dist": 1.0, "rr": 1.0,
                         "gate": (h1["close"].to_numpy() > h1["open"].to_numpy())[ok]})


def _gate_honest(m1):
    b15 = cl.build_bars(m1, "15min")
    ct = pd.DatetimeIndex(b15["close_time"])
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 1,
                         "stop_dist": 1.0, "rr": 1.0,
                         "gate": (b15["close"] > b15["open"]).to_numpy()})


@pytest.fixture(scope="module")
def short_m1():
    return make_m1(start="2019-01-07", end="2019-06-28", seed=5)


# ══ L1: a future FILTER passes a survival-only probe ═════════════════════════
def test_probe_catches_future_filter(short_m1):
    ev = _first15_of_hour(short_m1, leak=True)
    with pytest.raises(LookaheadError, match="cut data"):
        cl.probe_lookahead(lambda m: _first15_of_hour(m, True), ev, m1=short_m1,
                           lookback="3D")


def test_probe_passes_the_honest_twin(short_m1):
    ev = _first15_of_hour(short_m1, leak=False)
    out = cl.probe_lookahead(lambda m: _first15_of_hour(m, False), ev, m1=short_m1,
                             lookback="3D")
    assert out["passed"] and out["symmetric"] and out["n_cuts"] >= 100
    assert out["n_targeted"] == 20 and out["events_fp"] == cl.frame_fingerprint(ev)


# ══ L2: price columns were never compared ═══════════════════════════════════════
def test_probe_catches_future_stop_price(short_m1):
    ev = _future_stop(short_m1)
    ev = ev[np.isfinite(ev["stop_px"])].reset_index(drop=True)
    with pytest.raises(LookaheadError, match="stop_px"):
        cl.probe_lookahead(_future_stop, ev, m1=short_m1, lookback="3D")


def test_probe_cannot_ignore_harness_columns(short_m1):
    ev = _future_stop(short_m1)
    with pytest.raises(ValueError, match="cannot ignore"):
        cl.probe_lookahead(_future_stop, ev, m1=short_m1, ignore_cols=("stop_px",))


def test_probe_requires_detector_to_emit_every_scored_column(short_m1):
    ev = _first15_of_hour(short_m1, leak=False).assign(extra=1.0)
    with pytest.raises(ValueError, match="lacks columns"):
        cl.probe_lookahead(lambda m: _first15_of_hour(m, False), ev, m1=short_m1,
                           lookback="3D")


# ══ L3: gate masks had no behavioural check ══════════════════════════════════════
def test_probe_catches_inprogress_gate_column(short_m1):
    ev = _gate_inprogress(short_m1)
    with pytest.raises(LookaheadError, match="gate"):
        cl.probe_lookahead(_gate_inprogress, ev, m1=short_m1, lookback="3D")
    ok = cl.probe_lookahead(_gate_honest, _gate_honest(short_m1), m1=short_m1,
                            lookback="3D")
    assert ok["passed"] and "gate" in ok["columns"]


# ══ L4: write_result ignored the probe ═════════════════════════════════════════
@pytest.fixture(scope="module")
def honest_book(short_m1):
    ev = _first15_of_hour(short_m1, leak=False)
    probe = cl.probe_lookahead(lambda m: _first15_of_hour(m, False), ev, m1=short_m1,
                               lookback="3D")
    res = cl.trade_test(ev, max_hold="45min", m1=short_m1)
    return ev, probe, res


def _write(res, tmp_path, **kw):
    return cl.write_result("cisd", "rt", res, operationalization=kw.pop("op", OP),
                           params_source=kw.pop("src", SRC), script=__file__,
                           results_dir=tmp_path, **kw)


def test_write_refuses_without_probe(honest_book, tmp_path):
    _, _, res = honest_book
    with pytest.raises(ValueError, match="no probe_lookahead"):
        _write(res, tmp_path)


def test_write_refuses_failed_probe_even_with_declaration(honest_book, tmp_path):
    _, probe, res = honest_book
    bad = dict(probe, passed=False, failures=3)
    with pytest.raises(ValueError, match="FAILED"):
        _write(res, tmp_path, probe=bad, no_detector="clock rule")


def test_write_refuses_probe_of_a_different_frame(honest_book, short_m1, tmp_path):
    ev, probe, _ = honest_book
    res2 = cl.trade_test(ev.iloc[::2].reset_index(drop=True), max_hold="45min", m1=short_m1)
    with pytest.raises(ValueError, match="fingerprints differ"):
        _write(res2, tmp_path, probe=probe)


def test_write_refuses_a_thin_probe(honest_book, short_m1, tmp_path):
    ev, _, res = honest_book
    thin = cl.probe_lookahead(lambda m: _first15_of_hour(m, False), ev, m1=short_m1,
                              lookback="3D", n_cuts=10)
    with pytest.raises(ValueError, match="random cuts"):
        _write(res, tmp_path, probe=thin)


def test_write_accepts_matching_passing_probe(honest_book, tmp_path):
    _, probe, res = honest_book
    p = _write(res, tmp_path, probe=probe)
    doc = json.loads(p.read_text())
    assert doc["lookahead"]["probe"]["passed"] and doc["events_fp"] == probe["events_fp"]


def test_gate_mask_must_be_a_probed_column(short_m1, tmp_path):
    ev = _gate_honest(short_m1)
    probe = cl.probe_lookahead(_gate_honest, ev, m1=short_m1, lookback="3D")
    r_arr = cl.gate_test(ev, ev["gate"].to_numpy(), mask_available_at=ev["decision_time"],
                         max_hold="45min", m1=short_m1)
    with pytest.raises(ValueError, match="mask was passed as an array"):
        _write(r_arr, tmp_path, probe=probe)
    r_col = cl.gate_test(ev, "gate", mask_available_at="decision_time", max_hold="45min",
                         m1=short_m1)
    assert r_col["mask_col"] == "gate"
    _write(r_col, tmp_path, probe=probe)


def test_rate_needs_probed_predictors(short_m1, tmp_path):
    ev = _first15_of_hour(short_m1, leak=False)
    probe = cl.probe_lookahead(lambda m: _first15_of_hour(m, False), ev, m1=short_m1,
                               lookback="3D")
    t = pd.DatetimeIndex(ev["decision_time"])
    obs = np.random.default_rng(0).random(len(t)) < 0.5
    r0 = cl.rate_test(obs, t, available_at=t, null_p=np.full(len(t), .5), m1=short_m1)
    with pytest.raises(ValueError, match="predictors"):
        _write(r0, tmp_path, probe=probe)
    r1 = cl.rate_test(obs, t, available_at=t, null_p=np.full(len(t), .5), m1=short_m1,
                      predictors=ev)
    _write(r1, tmp_path, probe=probe)


# ══ L5: cache_frame keys collided across concepts / after a fix ═══════════════
@needs_real
def test_cache_frame_fingerprints_the_build(tmp_path, monkeypatch):
    import concept_lab.data as D
    monkeypatch.setattr(D, "CACHE_DIR", tmp_path)
    tag = "A"

    def build_a():
        return pd.DataFrame({"who": [tag], "shift": [-1]})

    def build_b():
        return pd.DataFrame({"who": ["B"], "shift": [0]})
    a = cl.cache_frame("fvg_15m", build_a)
    b = cl.cache_frame("fvg_15m", build_b)                      # same key, other code
    assert a["who"][0] == "A" and b["who"][0] == "B"
    assert cl.cache_frame("fvg_15m", build_a)["who"][0] == "A"  # a genuine hit
    assert len(list(tmp_path.glob("user_fvg_15m_*"))) == 2
    # a closure / global value the build reads is part of the fingerprint
    assert cl.build_fingerprint(lambda: tag * 2) != cl.build_fingerprint(lambda: tag * 3)

    def helper(k):
        return k + 1

    def outer():
        return helper(1)
    fp1 = cl.build_fingerprint(outer)

    def helper(k):                                               # noqa: F811 — "the fix"
        return k + 2

    def outer():                                                 # noqa: F811
        return helper(1)
    assert cl.build_fingerprint(outer) != fp1                    # callee edits count


# ══ L6: direction 0 / False traded as SHORT ══════════════════════════════════════
@pytest.mark.parametrize("bad", [0, 0.0, np.int64(0), False, True, np.nan, 2])
def test_direction_rejects_non_signals(flat_m1, bad):
    pos = event_positions(flat_m1, 60, seed=40)
    ev = events_at(flat_m1, pos, 1)
    ev["direction"] = ev["direction"].astype(object)
    ev.loc[5, "direction"] = bad
    with pytest.raises(ValueError, match="direction"):
        cl.trade_test(ev, max_hold="1h", m1=flat_m1)
    ev2 = events_at(flat_m1, pos, bad) if not isinstance(bad, bool) else None
    if ev2 is not None:
        with pytest.raises(ValueError, match="direction"):
            cl.trade_test(ev2, max_hold="1h", m1=flat_m1)


# ══ L7: NaT times read the last row of the dataset ═══════════════════════════════
def test_nat_lookups_return_nan(flat_m1):
    t = pd.DatetimeIndex([pd.Timestamp("2018-03-07 15:00", tz="UTC"), pd.NaT])
    d = cl.bars("1D", m1=flat_m1)
    a = cl.asof(d, t)
    assert np.isfinite(a["high"].iloc[0]) and np.isnan(a["high"].iloc[1])
    for kind in ("1D", "1W", "4h"):
        p = cl.prior_hilo(t, kind, m1=flat_m1)
        assert np.isfinite(p["high"].iloc[0]) and np.isnan(p["high"].iloc[1]), kind
        assert pd.isna(p["available_at"].iloc[1])


# ══ L8: NaT max_hold held trades to the end of the data ══════════════════════════
def test_nat_max_hold_raises(flat_m1):
    pos = event_positions(flat_m1, 100, seed=41)
    ev = events_at(flat_m1, pos, 1)
    hold = pd.Series([pd.Timedelta("2h")] * len(ev))
    hold.iloc[::2] = pd.NaT
    ev["max_hold"] = hold.to_numpy()
    with pytest.raises(ValueError, match="NaT"):
        cl.trade_test(ev, m1=flat_m1)


# ══ L9: bars() handed every caller the harness's own mutable frame ═══════════════
def test_bars_edits_do_not_leak_into_harness_lookups(flat_m1):
    t = pd.DatetimeIndex([pd.Timestamp("2020-03-12 15:00", tz="UTC")])
    before = cl.prior_hilo(t, "1D", m1=flat_m1)["high"].iloc[0]
    d = cl.bars("1D", m1=flat_m1)
    d["close_time"] = d.index                        # an agent-local edit
    d.loc[d.index[:50], "high"] = 0.0
    assert cl.bars("1D", m1=flat_m1) is not d
    assert cl.prior_hilo(t, "1D", m1=flat_m1)["high"].iloc[0] == before
    w = cl.window_hilo("ny_am", m1=flat_m1)
    w["high"] = -1.0
    assert (cl.window_hilo("ny_am", m1=flat_m1)["high"] > 0).all()


# ══ L10: stub sessions served as the prior day ═══════════════════════════════════
def test_prior_hilo_coverage_and_min_coverage():
    m1 = make_m1(start="2019-01-07", end="2019-02-28", seed=6)
    stub_day = pd.Timestamp("2019-01-16", tz="UTC")                # a Wednesday
    keep = ~((m1.index.normalize() == stub_day) &
             (m1.index < stub_day + pd.Timedelta(hours=16, minutes=40)))
    m = m1[keep]                                                   # 20 bars that day
    t = pd.DatetimeIndex([pd.Timestamp("2019-01-17 14:00", tz="UTC")])
    p = cl.prior_hilo(t, "1D", m1=m)
    assert p["n_m1"].iloc[0] == 20 and p["coverage"].iloc[0] < 0.2
    q = cl.prior_hilo(t, "1D", m1=m, min_coverage=0.5)
    assert q["n_m1"].iloc[0] == 240
    assert pd.Timestamp(q["available_at"].iloc[0]) < pd.Timestamp(p["available_at"].iloc[0])


# ══ S1: stop-first ties after volatility made spurious NEGATIVE / EDGE ═══════════
def test_tie_convention_cannot_decide_the_verdict():
    """Random direction, but 20% of the events sit on a volatility burst whose first
    M1 bar spans both the stop and the target: stop-first scores those as losses
    the random controls rarely suffer -> NEGATIVE (and EDGE under claim '-')."""
    base = make_m1(seed=50, start="2016-01-04", end="2021-12-31")
    pos = event_positions(base, 3000, seed=50, utc_hour=(14, 15))
    m1 = base.copy()
    hi, lo = m1["high"].to_numpy().copy(), m1["low"].to_numpy().copy()
    op = m1["open"].to_numpy()
    burst = pos[np.random.default_rng(1).random(len(pos)) < 0.2]
    hi[burst] = np.maximum(hi[burst], op[burst] + 1.2)
    lo[burst] = np.minimum(lo[burst], op[burst] - 1.2)
    m1["high"], m1["low"] = hi, lo
    dirs = np.random.default_rng(50).choice([-1, 1], len(pos))
    ev = events_at(m1, pos, dirs, stop_dist=1.0, rr=1.0)
    for claim, old in (("+", NEGATIVE), ("-", EDGE)):
        r = cl.trade_test(ev, max_hold="30min", m1=m1, claim=claim, n_boot=500,
                          blocks=False, ctrl_grid="m1")
        t = r["ties"]
        assert t["real_ambiguous"] - t["control_ambiguous"] > 0.15
        assert t["verdict_stop_first"] == old and not r["sanity_flags"]   # the artefact
        assert r["verdict"] == UNTESTABLE and "tie convention" in r["verdict_detail"]
        assert abs(t["diff_5050"]) < 0.03


def test_tie_rule_leaves_matched_books_alone(flat_m1):
    pos = event_positions(flat_m1, 1500, seed=51)
    dirs = np.random.default_rng(51).choice([-1, 1], len(pos))
    r = cl.trade_test(events_at(flat_m1, pos, dirs), max_hold="90min", m1=flat_m1,
                      n_boot=500, blocks=False)
    t = r["ties"]
    assert abs(t["real_ambiguous"] - t["control_ambiguous"]) <= 0.02
    assert "verdict_5050" not in t and r["verdict"] == t["verdict_stop_first"]


# ══ S2: rate_test rows sharing one outcome looked independent ════════════════════
def _rate_daily_book(m1, seed, n_boot=500):
    t = m1.index[(m1.index.minute % 5) == 0]              # 48 rows share each day's outcome
    td = np.asarray(cl.trading_day(t))
    days, di = np.unique(td, return_inverse=True)
    rng = np.random.default_rng(seed)
    obs = (rng.random(len(days)) < 0.4)[di].astype(float)
    return cl.rate_test(obs, t, available_at=t, null_p=np.full(len(t), 0.4), m1=m1,
                        n_boot=n_boot, blocks=False)


def test_rate_test_clusters_shared_outcomes(flat_m1):
    r = _rate_daily_book(flat_m1, 0)
    comps = r["ci_components"]
    w = {k: v[1] - v[0] for k, v in comps.items()}
    assert r["ci_method"] == "day_block"
    assert w["day_block"] > 1.3 * max(v for k, v in w.items() if k.startswith("phase3"))
    assert r["dependence"]["n_eff"] == r["dependence"]["n_days"] < r["n"]
    z = []
    for s in range(30):
        q = _rate_daily_book(flat_m1, 100 + s, n_boot=300)
        z.append(q["diff"] / ((q["ci_hi"] - q["ci_lo"]) / 3.92))
    assert (np.abs(z) > 1.96).sum() <= 5, z    # nominal 5% -> ~1.5 of 30 (old CI: ~8)


def test_rate_outcome_horizon_and_cluster(flat_m1):
    t = flat_m1.index[(flat_m1.index.minute % 15) == 0]
    wk = np.asarray(t.to_period("W").start_time)
    u, wi = np.unique(wk, return_inverse=True)
    obs = (np.random.default_rng(3).random(len(u)) < 0.4)[wi].astype(float)
    kw = dict(available_at=t, null_p=np.full(len(t), .4), m1=flat_m1, n_boot=500,
              blocks=False)
    r1 = cl.rate_test(obs, t, **kw)
    r5 = cl.rate_test(obs, t, outcome_horizon="5D", **kw)
    rc = cl.rate_test(obs, t, cluster=wi, **kw)
    assert "day_block_5d" in r5["ci_components"] and "cluster" in rc["ci_components"]
    w = lambda r: r["ci_hi"] - r["ci_lo"]                # noqa: E731
    assert w(r5) > 1.3 * w(r1) and w(rc) > 1.3 * w(r1)
    assert rc["dependence"]["n_eff"] == len(u)


# ══ S3: trade/gate CIs ignored setup clustering ══════════════════════════════════
def _setup_book(m1, seed, L=40, K=900):
    t = m1.index
    starts_ok = np.flatnonzero((t.hour == 14) & (t.minute == 0))
    rng = np.random.default_rng(seed)
    st = np.sort(rng.choice(starts_ok, K, replace=False))
    pos = (st[:, None] + np.arange(L)[None, :]).ravel()
    own = np.repeat(np.arange(K), L)
    dirs = rng.choice([-1, 1], K)[own]
    ev = events_at(m1, pos, dirs, stop_dist=2.0, rr=1.0)
    ev["setup"] = own
    ev["gate"] = (rng.random(K) < 0.4)[own]
    return ev


def _cluster_width(d, own, B=1000):
    u, inv = np.unique(own, return_inverse=True)
    s, c = np.bincount(inv, weights=d), np.bincount(inv)
    rng = np.random.default_rng(1)
    bs = [s[k].sum() / c[k].sum() for k in (rng.integers(0, len(u), len(u))
                                           for _ in range(B))]
    return np.percentile(bs, 97.5) - np.percentile(bs, 2.5)


def test_trade_ci_covers_setup_clustering(flat_m1):
    ev = _setup_book(flat_m1, 7)
    r = cl.trade_test(ev, max_hold="60min", m1=flat_m1, n_boot=1000, blocks=False,
                      keep_trades=True)
    tr = r["_trades"]
    d = (tr["net_R"] - tr["ctrl_mean_R"]).to_numpy()
    own = ev["setup"].to_numpy()[tr["ev_id"]]
    ok = np.isfinite(d)
    wc = _cluster_width(d[ok], own[ok])
    w = r["ci_hi"] - r["ci_lo"]
    p3 = max(v[1] - v[0] for k, v in r["ci_components"].items() if k.startswith("phase3"))
    assert p3 < 0.85 * wc                 # the old CI was too narrow ...
    assert w >= 0.9 * wc                  # ... the reported one is not
    rc = cl.trade_test(ev, max_hold="60min", m1=flat_m1, n_boot=1000, blocks=False,
                       cluster="setup")
    assert "cluster" in rc["ci_components"] and rc["dependence"]["n_clusters"] == 900
    assert rc["dependence"]["n_eff"] <= 900


def test_gate_ci_covers_setup_clustering(flat_m1):
    ev = _setup_book(flat_m1, 8)
    r = cl.gate_test(ev, "gate", mask_available_at="decision_time", max_hold="60min",
                     m1=flat_m1, n_boot=1000, blocks=False)
    p3 = max(v[1] - v[0] for k, v in r["ci_components"].items() if k.startswith("phase3"))
    assert r["ci_method"] == "day_block" and (r["ci_hi"] - r["ci_lo"]) > 1.2 * p3
    assert r["dependence"]["n_eff"] <= min(r["n"], r["n_complement"])


def test_dependence_length_tracks_same_direction_runs(flat_m1):
    """A 'daily bias' book (every 15m mark of a day, one direction per day) has a
    dependence length of more than one day; a sparse book has one day."""
    t = flat_m1.index
    g = np.flatnonzero(t.minute % 15 == 0)
    td = np.asarray(cl.trading_day(t[g]))
    days, di = np.unique(td, return_inverse=True)
    rng = np.random.default_rng(9)
    dirs = rng.choice([-1, 1], len(days))[di]
    ev = events_at(flat_m1, g, dirs, stop_dist=3.0, rr=2.0)
    # the synthetic venue shuts 20h a day: a 22h hold chains same-direction days
    r = cl.trade_test(ev, max_hold="22h", m1=flat_m1, n_boot=300, blocks=False)
    assert r["dependence"]["day_block_mean_days"] >= 2
    sparse = events_at(flat_m1, event_positions(flat_m1, 800, seed=9), 1)
    r2 = cl.trade_test(sparse, max_hold="1h", m1=flat_m1, n_boot=300, blocks=False)
    assert r2["dependence"]["day_block_mean_days"] == 1


# ══ S5: controls that ARE the concept's own trades ═══════════════════════════════
def test_control_overlap_is_reported_and_blocks_null(flat_m1):
    t = flat_m1.index
    g = np.flatnonzero(t.minute % 15 == 0)
    c = flat_m1["close"].to_numpy()
    mom = np.sign(pd.Series(c).diff(240 * 20).to_numpy())       # ~20-day momentum
    ok = np.isfinite(mom[g]) & (mom[g] != 0)
    ev = events_at(flat_m1, g[ok], mom[g][ok].astype(int), stop_dist=3.0, rr=2.0)
    r = cl.trade_test(ev, max_hold="1h", m1=flat_m1, n_boot=300, blocks=False)
    assert r["ctrl_overlap"] > 0.2
    assert r["verdict"] != NULL
    sparse = events_at(flat_m1, event_positions(flat_m1, 800, seed=11), 1)
    r2 = cl.trade_test(sparse, max_hold="1h", m1=flat_m1, n_boot=300, blocks=False)
    assert r2["ctrl_overlap"] < rules_mod.CTRL_OVERLAP_MAX


# ══ S4 + S6: every run is ledgered and counted; knobs cannot be re-rolled ════════
def test_ledger_counts_unwritten_readings(flat_m1, tmp_path, monkeypatch):
    led = tmp_path / "ledger.jsonl"
    monkeypatch.setenv("CONCEPT_LAB_LEDGER", str(led))
    res_dir = tmp_path / "res"
    pos = event_positions(flat_m1, 400, seed=60)
    a = cl.trade_test(events_at(flat_m1, pos, 1), max_hold="90min", m1=flat_m1)
    cl.trade_test(events_at(flat_m1, pos, -1), max_hold="90min", m1=flat_m1)   # reading 2
    cl.trade_test(events_at(flat_m1, pos, -1), max_hold="90min", m1=flat_m1,
                  seed=5)                                           # same hypothesis
    lines = led.read_text().splitlines()
    assert len(lines) == 3 and a["run_id"] == json.loads(lines[0])["run_id"]
    cl.write_result("cisd", "r1", a, operationalization=OP, params_source=SRC,
                    script=__file__, results_dir=res_dir, no_detector="clock rule")
    df = cl.adjust_campaign(res_dir)
    assert df.attrs["family_size"] == 2 and df.attrs["unwritten_hypotheses"] == 1
    assert cl.adjust_campaign(res_dir, ledger=False).attrs["family_size"] == 1


def test_write_refuses_disabled_ledger(flat_m1, tmp_path, monkeypatch):
    monkeypatch.setenv("CONCEPT_LAB_LEDGER_DISABLE", "1")
    pos = event_positions(flat_m1, 300, seed=61)
    r = cl.trade_test(events_at(flat_m1, pos, 1), max_hold="90min", m1=flat_m1)
    assert r["run_id"] is None
    with pytest.raises(ValueError, match="ledger"):
        _write(r, tmp_path, no_detector="clock rule")


@pytest.mark.parametrize("kw,msg", [
    (dict(seed=7), "seed"), (dict(n_boot=500), "n_boot"), (dict(reps=3), "reps"),
    (dict(window_days=10), "window_days"), (dict(entry_mode="prev_close"), "entry_mode"),
    (dict(hold_basis="bars"), "hold_basis"), (dict(ctrl_tod_tol_min=30), "ctrl_tod_tol_min"),
])
def test_write_refuses_rerolled_or_undeclared_knobs(flat_m1, tmp_path, kw, msg):
    pos = event_positions(flat_m1, 300, seed=62)
    r = cl.trade_test(events_at(flat_m1, pos, 1), max_hold="90min", m1=flat_m1, **kw)
    with pytest.raises(ValueError, match=msg):
        _write(r, tmp_path, no_detector="clock rule")


def test_declared_knob_is_accepted(flat_m1, tmp_path):
    pos = event_positions(flat_m1, 300, seed=63)
    r = cl.trade_test(events_at(flat_m1, pos, 1), max_hold="90min", m1=flat_m1,
                      hold_basis="bars")
    src = dict(SRC, hold_basis="declared-before-run: events cluster before the halt")
    _write(r, tmp_path, src=src, no_detector="clock rule")
