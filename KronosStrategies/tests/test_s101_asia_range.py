"""S101 Asia-session range fade -- synthetic, no DB, no network."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

_STRAT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "strategies"))
if _STRAT_DIR not in sys.path:
    sys.path.insert(0, _STRAT_DIR)

from backtest_strategies import s101_asia_range as s  # noqa: E402
from strategy.entry_manager import _VARIATION_STRATEGY_NAME  # noqa: E402

NOW = datetime(2026, 11, 12, 3, 0, tzinfo=timezone.utc)


def _frame(closes):
    c = np.asarray(closes, float)
    return pd.DataFrame({"time": pd.date_range("2026-11-12", periods=len(c), freq="1min", tz="UTC"),
                         "open": c, "high": c + 0.2, "low": c - 0.2, "close": c, "volume": 1})


def _osc(last5, top=True):
    """160 minutes oscillating 4000..4020 whose value 120 minutes ago equals where it ends (top or bottom), then the given last 5 closes."""
    i = np.arange(160); wave = 10 * np.cos(2 * np.pi * (i - 39) / 60)
    base = 4010 + (wave if top else -wave)
    return _frame(list(base[:-5]) + list(last5))


def test_registered_and_window():
    assert s.NAME in _VARIATION_STRATEGY_NAME
    assert s.MIN_BARS_1M == 150 and s.CONFIG.session_start_hour == 0 and s.CONFIG.session_end_hour == 8


def test_sell_at_top_after_push_up():
    sig = s.get_signal(_osc([4013, 4015, 4017, 4018.5, 4019.5]), None, None, NOW)
    assert sig is not None and sig.side == "SELL"
    assert sig.take_profit == sig.entry_price - 8 and sig.stop_loss == sig.entry_price + 24
    assert sig.max_hold_min == (20 * 60 + 50) - 3 * 60


def test_buy_at_bottom_after_push_down():
    sig = s.get_signal(_osc([4007, 4005, 4003, 4001.5, 4000.5], top=False), None, None, NOW)
    assert sig is not None and sig.side == "BUY"
    assert sig.take_profit == sig.entry_price + 8 and sig.stop_loss == sig.entry_price - 24


def test_no_signal_mid_range_or_without_push():
    assert s.get_signal(_osc([4010, 4010, 4010, 4010, 4010]), None, None, NOW) is None
    assert s.get_signal(_osc([4019.0, 4018.8, 4018.7, 4018.7, 4018.6]), None, None, NOW) is None   # near the top, but drifting down: no push up


def test_no_signal_when_trending_or_range_small():
    trend = _frame(np.linspace(4000, 4060, 160))                 # one-way move: net move ~ the whole range
    assert s.get_signal(trend, None, None, NOW) is None
    tiny = _frame(4010 + 2 * np.sin(np.linspace(0, 6 * np.pi, 160)))
    assert s.get_signal(tiny, None, None, NOW) is None


def test_short_window_returns_none():
    assert s.get_signal(_osc([4013, 4015, 4017, 4018.5, 4019.5]).tail(100), None, None, NOW) is None
