"""A look-ahead event must RAISE, in every test type; the entry is never on the
signal bar; the behavioural probe catches a detector that peeks."""
import numpy as np
import pandas as pd
import pytest

import concept_lab as cl
from concept_lab import LookaheadError
from conftest import events_at, event_positions


def test_trade_event_deciding_before_its_inputs_raises(flat_m1):
    pos = event_positions(flat_m1, 300, seed=0)
    ev = events_at(flat_m1, pos, 1)
    ev.loc[17, "available_at"] = ev.loc[17, "decision_time"] + pd.Timedelta("1min")
    with pytest.raises(LookaheadError):
        cl.trade_test(ev, max_hold="1h", m1=flat_m1)


def test_htf_bar_in_progress_raises(flat_m1):
    """Trap 9: deciding at 14:30 with the 14:00 1h bar (closes 15:00)."""
    b = cl.bars("1h", m1=flat_m1)
    starts = b.index[(b.index.hour == 14)][:200]
    ev = pd.DataFrame({"decision_time": starts + pd.Timedelta("30min"),
                       "available_at": b.loc[starts, "close_time"].to_numpy(),
                       "direction": 1, "stop_dist": 2.0, "rr": 1.0})
    with pytest.raises(LookaheadError):
        cl.trade_test(ev, max_hold="1h", m1=flat_m1)


def test_nat_available_at_raises(flat_m1):
    pos = event_positions(flat_m1, 100, seed=1)
    ev = events_at(flat_m1, pos, 1)
    ev["available_at"] = ev["available_at"].astype("object")
    ev.loc[3, "available_at"] = pd.NaT
    with pytest.raises(LookaheadError):
        cl.trade_test(ev, max_hold="1h", m1=flat_m1)


def test_gate_mask_from_the_future_raises(flat_m1):
    pos = event_positions(flat_m1, 400, seed=2)
    ev = events_at(flat_m1, pos, 1)
    mask = np.arange(len(ev)) % 2 == 0
    late = ev["decision_time"] + pd.Timedelta("5min")
    with pytest.raises(LookaheadError):
        cl.gate_test(ev, mask, mask_available_at=late, max_hold="1h", m1=flat_m1)
    bad = mask.astype(object)
    bad[4] = None
    with pytest.raises(ValueError):
        cl.gate_test(ev, bad, mask_available_at=ev["decision_time"], max_hold="1h",
                     m1=flat_m1)


def test_rate_predictor_from_the_future_raises(flat_m1):
    t = flat_m1.index[event_positions(flat_m1, 300, seed=3)]
    with pytest.raises(LookaheadError):
        cl.rate_test(np.ones(len(t)), t, available_at=t + pd.Timedelta("1min"),
                     null_p=np.full(len(t), .5), m1=flat_m1)


def test_entry_is_never_on_the_signal_bar():
    """The signal bar (10:00-11:00) tags the stop; the bars AFTER it run to target.
    A harness that replays the signal bar returns a loss; the correct one a win."""
    idx = pd.date_range("2021-03-01 10:00", periods=180, freq="1min", tz="UTC")
    o = np.full(180, 100.0)
    h = np.full(180, 100.2)
    lo = np.full(180, 99.8)
    c = np.full(180, 100.0)
    lo[30] = 97.0                                   # inside the signal bar: stop tagged
    c[60:] = o[60:] = np.linspace(100, 104, 120)    # after the close: rally
    h[60:] = c[60:] + 0.1
    lo[60:] = c[60:] - 0.1
    m1 = pd.DataFrame({"open": o, "high": h, "low": lo, "close": c}, index=idx)
    bars = cl.build_bars(m1, "1h")
    sig = bars.index[0]
    dec = bars.loc[sig, "close_time"]                # 11:00
    ev = pd.DataFrame({"decision_time": [dec, dec - pd.Timedelta("30s")],
                       "available_at": [dec, dec - pd.Timedelta("30s")],
                       "direction": [1, 1], "stop_px": [98.0, 98.0], "rr": [1.0, 1.0]})
    r = cl.trade_test(ev, max_hold="2h", keep_trades=True, m1=m1, blocks=False, reps=1)
    tr = r["_trades"]
    assert (tr["entry_time"] >= pd.Timestamp("2021-03-01 11:00", tz="UTC")).all()
    assert (tr["entry_time"] >= tr["decision_time"]).all()
    assert list(tr["reason"]) == ["target", "target"]
    assert r["lookahead"]["passed"] and r["lookahead"]["entry_min_delay_min"] >= 0


def _honest(m1):
    b = cl.build_bars(m1, "1h")
    sel = b["close"] > b["open"] + 1.0
    return pd.DataFrame({"decision_time": b.loc[sel, "close_time"].to_numpy(),
                         "direction": 1})


def _peeking(m1):
    b = cl.build_bars(m1, "1h")
    sel = b["close"].shift(-1) > b["close"] + 1.0     # reads the NEXT bar
    return pd.DataFrame({"decision_time": b.loc[sel, "close_time"].to_numpy(),
                         "direction": 1})


def test_probe_lookahead_passes_honest_and_catches_peeking(flat_m1):
    honest = _honest(flat_m1)
    out = cl.probe_lookahead(_honest, honest, m1=flat_m1, n_sample=15, lookback="3D")
    assert out["passed"] and out["sampled"] == 15
    peek = _peeking(flat_m1)
    with pytest.raises(LookaheadError):
        cl.probe_lookahead(_peeking, peek, m1=flat_m1, n_sample=15, lookback="3D")
