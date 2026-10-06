"""Claude Strategy guard — the limits the Claude session trades under."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "strategies"))

import pytest

import claude_guard as g


@pytest.mark.parametrize("pnl,want", [
    (0.0, None), (99.99, None), (100.0, "target_hit"), (250.0, "target_hit"),
    (-99.99, None), (-100.0, "loss_limit_hit"), (-180.0, "loss_limit_hit"),
])
def test_day_lock_edges(pnl, want):
    assert g.day_lock(pnl) == want


def test_size_lots_risks_at_most_budget():
    assert g.size_lots(5.0, 0.10) == 0.05            # 0.05 * 5 * 100 = 25
    assert g.size_lots(2.0, 0.10) == 0.10            # 0.125 capped by MAX_LOT
    assert g.size_lots(30.0, 0.10) is None           # 0.01 lot risks 30 > 25


def test_size_lots_float_edge():
    # 25 / (25/29 * 100) = 0.29 exactly in theory; float gives 0.2899999…
    assert g.size_lots(25 / 29, 1.0) == 0.29


def test_check_open_ok_buy_and_sell():
    lots, why = g.check_open("BUY", 4130.0, 4125.0, 4140.0, 0.0, False, 0.10)
    assert lots == 0.05 and why.startswith("ok")
    lots, _ = g.check_open("SELL", 4130.0, 4135.0, 4120.0, -40.0, False, 0.10)
    assert lots == 0.05


@pytest.mark.parametrize("side,sl,tp,reason", [
    ("BUY", 4135.0, 4140.0, "bad_levels"),      # SL above entry on a buy
    ("BUY", 4125.0, 4132.0, "ok"),              # small RR is allowed
    ("SELL", 4125.0, 4120.0, "bad_levels"),     # SL below entry on a sell
    ("HOLD", 4125.0, 4140.0, "bad_side"),
    ("BUY", 4129.5, 4140.0, "sl_too_tight"),
    ("BUY", 4095.0, 4200.0, "sl_too_wide"),
])
def test_check_open_level_validation(side, sl, tp, reason):
    lots, why = g.check_open(side, 4130.0, sl, tp, 0.0, False, 0.10)
    assert why.startswith(reason)
    assert (lots is None) == (reason != "ok")


def test_check_open_one_trade_and_day_lock():
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, 0.0, True, 0.10)[1].startswith("open_position_cap")
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, 100.0, False, 0.10)[1] == "day_locked:target_hit"
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, -100.0, False, 0.10)[1] == "day_locked:loss_limit_hit"


def test_check_open_refuses_breaching_the_loss_limit():
    # day -80, $25 at risk -> worst -105 -> refused; day -75 -> worst exactly -100 -> allowed
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, -80.0, False, 0.10)[1].startswith("would_breach")
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, -75.0, False, 0.10)[0] == 0.05
