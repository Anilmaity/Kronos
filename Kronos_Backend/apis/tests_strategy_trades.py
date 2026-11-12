from django.test import SimpleTestCase

from apis.schema import schema
from apis.schema.query.strategy_trades import simulate


class SimulateTests(SimpleTestCase):
    bars = [(60, 100, 101, 99, 100), (120, 100, 109, 99.5, 108), (180, 108, 108, 75, 76)]

    def test_buy_hits_target(self):
        (t,) = simulate([(60, "BUY", 100.0, 76.0, 108.0, "")], self.bars)
        self.assertEqual((t["outcome"], t["pnlUsd"], t["exitTime"]), ("TP", 8.0, 180))

    def test_stop_wins_when_both_touch_in_one_bar(self):
        (t,) = simulate([(120, "BUY", 108.0, 76.0, 108.0, "")], self.bars)
        self.assertEqual((t["outcome"], t["pnlUsd"]), ("SL", -32.0))

    def test_sell_and_unresolved_signal_dropped(self):
        self.assertEqual(simulate([(180, "SELL", 76.0, 100.0, 68.0, "")], self.bars), [])
        (t,) = simulate([(60, "SELL", 100.0, 109.0, 92.0, "")], self.bars)
        self.assertEqual(t["outcome"], "SL")

    def test_schema_exposes_fields(self):
        s = str(schema)
        self.assertIn("strategyTrades", s)
        self.assertIn("RunStrategyBacktest", s)
